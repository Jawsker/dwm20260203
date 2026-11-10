"""Orders Service (privado). Dueño del pedido, su máquina de estados y su ciclo de reserva/pago.

Reglas que el navegador NO decide: precios (se leen de inventory), total, estado y "pagado".
Un pedido solo pasa a ``paid`` cuando Payments informa un pago verificado por su webhook firmado
y el monto coincide con el total guardado aquí.

Estados:  pending_reservation -> awaiting_payment -> paid -> preparing -> ready -> delivered
          pending_reservation -> rejected | expired      awaiting_payment -> cancelled | expired
          expired|cancelled|rejected + pago tardío -> refund_required
"""
from __future__ import annotations

import hashlib
import os
import secrets as pysecrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lr_common.client import ServiceClient
from lr_common.db import db_ping, get_db
from lr_common.web import ApiError, Edge, Identity, create_app, edge_guard

SERVICE = "orders"
db = get_db(SERVICE)
app = create_app(SERVICE, ready_checks={"db": lambda: db_ping(db)})
guard = edge_guard(SERVICE, allowed=["gateway", "graphql", "payments"], identity_from=["gateway", "graphql"])
inventory = ServiceClient(SERVICE, "inventory", "LR_INVENTORY_URL", "http://inventory:8000", timeout=3.0)
payments = ServiceClient(SERVICE, "payments", "LR_PAYMENTS_URL", "http://payments:8000", timeout=4.0)

TTL = int(os.getenv("LR_ORDER_TTL_SECONDS", "900"))
RESERVING_TIMEOUT = int(os.getenv("LR_RESERVING_TIMEOUT_SECONDS", "60"))
SWEEP_EVERY = int(os.getenv("LR_SWEEP_INTERVAL_SECONDS", "30"))

STAFF_FLOW = {"paid": "preparing", "preparing": "ready", "ready": "delivered"}  # origen -> único destino
PAID_OR_LATER = ("paid", "preparing", "ready", "delivered")
OPEN_STATES = ("pending_reservation", "awaiting_payment")


def now() -> datetime:  # UTC "naive": así lo almacena y devuelve MongoDB
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(d: Optional[datetime]) -> Optional[str]:
    return d.isoformat(timespec="seconds") + "Z" if d else None


def entry(status: str, by: str, reason: Optional[str] = None) -> dict:
    return {"status": status, "at": now(), "by": by, **({"reason": reason} if reason else {})}


def transition(order_id: str, from_states: tuple | list, to: str, by: str, reason: Optional[str] = None,
               extra: Optional[dict] = None) -> Optional[dict]:
    """Cambio de estado atómico: solo ocurre si el pedido sigue en un estado de origen permitido."""
    return db.orders.find_one_and_update(
        {"_id": order_id, "status": {"$in": list(from_states)}},
        {"$set": {"status": to, "updated_at": now(), **(extra or {})}, "$push": {"history": entry(to, by, reason)}},
        return_document=ReturnDocument.AFTER,
    )


def view(o: dict, ident: Identity) -> dict:
    out = {
        "id": o["_id"], "status": o["status"], "total": o["total"], "currency": "CLP",
        "created_at": iso(o["created_at"]), "expires_at": iso(o.get("expires_at")),
        "items": [{"product_id": i["product_id"], "nombre": i["nombre"], "qty": i["qty"],
                   "unit_price": i["unit_price"], "subtotal": i["subtotal"]} for i in o["items"]],
        "payment": {"status": (o.get("payment") or {}).get("status", "none")},
        "refund_required": o["status"] == "refund_required",
    }
    if ident.role == "auditor":  # supervisa sin ver quién compró ni notas
        out["customer_ref"] = hashlib.sha256(o["user_id"].encode()).hexdigest()[:10]
    else:
        out["customer_id"] = o["user_id"]
        out["notes"] = o.get("notes")
    return out


def load_for(order_id: str, ident: Identity) -> dict:
    o = db.orders.find_one({"_id": order_id})
    # 404 (y no 403) para pedidos ajenos: no se revela si el identificador existe.
    if not o or (ident.role == "customer" and o["user_id"] != ident.user_id):
        raise ApiError(404, "not_found", "Pedido no encontrado.")
    return o


class Line(BaseModel):
    product_id: str = Field(min_length=1, max_length=40)
    qty: int = Field(ge=1, le=20)


class NewOrder(BaseModel):
    # Nótese: NO hay campos de precio, total ni estado. Si llegan, se ignoran (extra='ignore').
    items: list[Line] = Field(min_length=1, max_length=30)
    notes: Optional[str] = Field(default=None, max_length=200)


class StatusChange(BaseModel):
    status: str = Field(pattern=r"^(preparing|ready|delivered)$")


class PaymentResult(BaseModel):
    payment_id: str = Field(max_length=60)
    status: str = Field(pattern=r"^(succeeded|failed)$")
    amount: int = Field(ge=0)
    event_id: str = Field(max_length=80)


class Anonymize(BaseModel):
    user_id: str = Field(max_length=40)


@app.post("/internal/orders", status_code=201)
def create_order(body: NewOrder, edge: Edge = Depends(guard), idempotency_key: Optional[str] = Header(default=None)):
    ident = edge.need_identity().require("customer")
    ids = [l.product_id for l in body.items]
    if len(set(ids)) != len(ids):
        raise ApiError(400, "duplicate_items", "Un producto aparece repetido; suma las cantidades.")
    order_id = "LR-" + pysecrets.token_hex(4).upper()
    if idempotency_key:
        if len(idempotency_key) > 80:
            raise ApiError(400, "validation_error", "Idempotency-Key demasiado larga.")
        try:
            db.idempotency.insert_one({"_id": f"{ident.user_id}:{idempotency_key}", "order_id": order_id, "at": now()})
        except DuplicateKeyError:
            prev = db.idempotency.find_one({"_id": f"{ident.user_id}:{idempotency_key}"})
            return view(load_for(prev["order_id"], ident), ident) | {"replayed": True}

    # Precios y nombres vigentes, desde la autoridad (inventory). El navegador no aporta precios.
    catalog = {p["id"]: p for p in inventory.call("POST", "/internal/products/batch", json={"ids": ids})["items"]}
    missing = [i for i in ids if i not in catalog]
    if missing:
        raise ApiError(409, "product_unavailable", "Hay productos que ya no existen en el catálogo.",
                       [{"product_id": m} for m in missing])
    lines = [{"product_id": l.product_id, "nombre": catalog[l.product_id]["nombre"], "qty": l.qty,
              "unit_price": catalog[l.product_id]["precio"], "subtotal": catalog[l.product_id]["precio"] * l.qty}
             for l in body.items]
    t = now()
    order = {"_id": order_id, "user_id": ident.user_id, "items": lines, "total": sum(l["subtotal"] for l in lines),
             "notes": body.notes, "status": "pending_reservation", "created_at": t, "updated_at": t,
             "payment": None, "history": [entry("pending_reservation", "customer")]}
    db.orders.insert_one(order)

    try:
        inventory.call("POST", "/internal/reservations", json={"order_id": order_id, "items": [
            {"product_id": l["product_id"], "qty": l["qty"]} for l in lines]})
    except ApiError as exc:
        # 409 = el stock no alcanza (rechazo de negocio). Otros = inventory caído/lento: reserva desconocida.
        unknown = exc.status >= 500
        transition(order_id, ["pending_reservation"], "rejected", "system", exc.code,
                   extra={"release_pending": unknown})
        raise
    updated = transition(order_id, ["pending_reservation"], "awaiting_payment", "system",
                         extra={"expires_at": now() + timedelta(seconds=TTL)})
    return view(updated, ident)


@app.get("/internal/orders")
def list_orders(status: Optional[str] = None, limit: int = 20, offset: int = 0, edge: Edge = Depends(guard)):
    ident = edge.need_identity()
    if not 1 <= limit <= 50 or offset < 0:
        raise ApiError(400, "invalid_filter", "Paginación fuera de rango (limit 1-50).")
    flt: dict = {}
    if ident.role == "customer":
        flt["user_id"] = ident.user_id  # el filtro lo impone el servidor, no el cliente
    if status:
        flt["status"] = status
    total = db.orders.count_documents(flt)
    rows = list(db.orders.find(flt).sort("created_at", -1).skip(offset).limit(limit))
    return {"items": [view(o, ident) for o in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/internal/orders/summary")
def summary(edge: Edge = Depends(guard)):
    edge.need_identity().require("staff", "admin", "auditor")
    counts: dict[str, int] = {}
    sales = 0
    # Agregación en la base (no se traen los pedidos al servicio): $group por estado.
    for row in db.orders.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}, "ventas": {"$sum": "$total"}}}]):
        counts[row["_id"]] = row["n"]
        if row["_id"] in PAID_OR_LATER:
            sales += row["ventas"]
    return {"by_status": counts, "paid_sales": sales}


@app.get("/internal/orders/{order_id}")
def get_order(order_id: str, edge: Edge = Depends(guard)):
    ident = edge.need_identity()
    return view(load_for(order_id, ident), ident)


@app.post("/internal/orders/{order_id}/pay")
def pay_order(order_id: str, edge: Edge = Depends(guard)):
    ident = edge.need_identity().require("customer")
    o = load_for(order_id, ident)
    if o["status"] != "awaiting_payment":
        raise ApiError(409, "invalid_state", f"El pedido está en estado {o['status']} y no admite pago.")
    if o["expires_at"] <= now():
        raise ApiError(409, "order_expired", "El pedido expiró; arma uno nuevo.")
    # El monto sale del pedido guardado, nunca de la solicitud.
    pay = payments.call("POST", "/internal/payments", json={"order_id": order_id, "user_id": o["user_id"], "amount": o["total"]})
    db.orders.update_one({"_id": order_id}, {"$set": {"payment": {"id": pay["payment_id"], "status": pay["status"]}}})
    return {"order_id": order_id, "payment_id": pay["payment_id"], "provider_ref": pay["provider_ref"], "amount": o["total"]}


def _release(order_id: str) -> bool:
    try:
        inventory.call("POST", f"/internal/reservations/{order_id}/release")
        return True
    except ApiError as exc:
        return exc.status == 404  # no había reserva: nada que liberar


@app.post("/internal/orders/{order_id}/cancel")
def cancel_order(order_id: str, edge: Edge = Depends(guard)):
    ident = edge.need_identity().require("customer", "staff", "admin")
    load_for(order_id, ident)
    updated = transition(order_id, ["awaiting_payment"], "cancelled", ident.role)
    if updated is None:
        raise ApiError(409, "invalid_state", "Solo se puede cancelar un pedido pendiente de pago.")
    if not _release(order_id):
        db.orders.update_one({"_id": order_id}, {"$set": {"release_pending": True}})
    return view(updated, ident)


@app.post("/internal/orders/{order_id}/status")
def change_status(order_id: str, body: StatusChange, edge: Edge = Depends(guard)):
    ident = edge.need_identity().require("staff", "admin")
    o = load_for(order_id, ident)
    if STAFF_FLOW.get(o["status"]) != body.status:
        raise ApiError(409, "invalid_transition", f"No se puede pasar de {o['status']} a {body.status}.")
    updated = transition(order_id, [o["status"]], body.status, ident.role)
    if updated is None:  # alguien cambió el estado en paralelo
        raise ApiError(409, "invalid_transition", "El estado cambió mientras lo modificabas.")
    return view(updated, ident)


@app.post("/internal/orders/{order_id}/payment-result")
def payment_result(order_id: str, body: PaymentResult, edge: Edge = Depends(guard)):
    """Solo Payments puede llamar aquí (clave de arista orders<-payments)."""
    if edge.caller != "payments":
        raise ApiError(403, "forbidden", "Solo el servicio de pagos informa resultados de pago.")
    o = db.orders.find_one({"_id": order_id})
    if not o:
        raise ApiError(404, "not_found", "Pedido no encontrado.")
    if body.amount != o["total"]:
        app.state.log.warning("monto_inconsistente", extra={"order": order_id})
        raise ApiError(409, "amount_mismatch", "El monto pagado no coincide con el total del pedido.")
    if body.status == "failed":
        if o["status"] == "awaiting_payment":
            db.orders.update_one({"_id": order_id}, {"$set": {"payment": {"id": body.payment_id, "status": "failed"}},
                                                      "$inc": {"payment_attempts": 1}})
        return {"order_id": order_id, "status": o["status"], "replayed": False}
    # --- pago exitoso verificado por Payments ---
    if o["status"] in PAID_OR_LATER:
        return {"order_id": order_id, "status": o["status"], "replayed": True}
    if o["status"] == "awaiting_payment":
        updated = transition(order_id, ["awaiting_payment"], "paid", "payments",
                             extra={"payment": {"id": body.payment_id, "status": "succeeded"}})
        if updated is None:  # carrera con expiración/cancelación: se resuelve como pago tardío
            o = db.orders.find_one({"_id": order_id})
        else:
            try:
                inventory.call("POST", f"/internal/reservations/{order_id}/commit")
            except ApiError:
                db.orders.update_one({"_id": order_id}, {"$set": {"commit_pending": True}})  # reintenta el barrido
            return {"order_id": order_id, "status": "paid", "replayed": False}
    # Pago recibido cuando el pedido ya expiró/canceló: el dinero entró y la reserva ya no existe.
    updated = transition(order_id, ["expired", "cancelled", "rejected"], "refund_required", "payments", "late_payment",
                         extra={"payment": {"id": body.payment_id, "status": "succeeded"}})
    return {"order_id": order_id, "status": "refund_required" if updated else o["status"], "replayed": updated is None}


@app.post("/internal/orders/anonymize")
def anonymize(body: Anonymize, edge: Edge = Depends(guard)):
    """Eliminación de cuenta: se conservan los pedidos pagados (registro comercial) sin datos personales."""
    ident = edge.need_identity()
    if ident.user_id != body.user_id and ident.role != "admin":
        raise ApiError(403, "forbidden", "Solo puedes anonimizar tus propios pedidos.")
    alias = "deleted-" + hashlib.sha256(body.user_id.encode()).hexdigest()[:10]
    res = db.orders.update_many({"user_id": body.user_id}, {"$set": {"user_id": alias, "notes": None, "customer_deleted": True}})
    return {"anonymized": res.modified_count}


def run_sweep() -> dict:
    """Barrido: expira pedidos vencidos, libera stock y reintenta operaciones pendientes con inventory."""
    t = now()
    out = {"expired": 0, "released_retried": 0, "commits_retried": 0}
    stuck_before = t - timedelta(seconds=RESERVING_TIMEOUT)
    for o in list(db.orders.find({"status": "awaiting_payment", "expires_at": {"$lte": t}})):
        if transition(o["_id"], ["awaiting_payment"], "expired", "system", "ttl"):
            out["expired"] += 1
            if not _release(o["_id"]):
                db.orders.update_one({"_id": o["_id"]}, {"$set": {"release_pending": True}})
    for o in list(db.orders.find({"status": "pending_reservation", "created_at": {"$lte": stuck_before}})):
        if transition(o["_id"], ["pending_reservation"], "expired", "system", "reserving_timeout"):
            out["expired"] += 1
            if not _release(o["_id"]):
                db.orders.update_one({"_id": o["_id"]}, {"$set": {"release_pending": True}})
    for o in list(db.orders.find({"release_pending": True})):
        if _release(o["_id"]):
            db.orders.update_one({"_id": o["_id"]}, {"$set": {"release_pending": False}})
            out["released_retried"] += 1
    for o in list(db.orders.find({"commit_pending": True})):
        try:
            inventory.call("POST", f"/internal/reservations/{o['_id']}/commit")
            db.orders.update_one({"_id": o["_id"]}, {"$set": {"commit_pending": False}})
            out["commits_retried"] += 1
        except ApiError:
            pass
    return out


@app.post("/internal/orders/maintenance/sweep")
def sweep(edge: Edge = Depends(guard)):
    edge.need_identity().require("admin")
    return run_sweep()


def _loop() -> None:
    while True:
        time.sleep(SWEEP_EVERY)
        try:
            run_sweep()
        except Exception:  # noqa: BLE001 - el barrido nunca debe tumbar el servicio
            app.state.log.error("sweep_failed", exc_info=True)


db.orders.create_index([("user_id", 1), ("created_at", -1)])
db.orders.create_index("status")
if SWEEP_EVERY > 0:
    threading.Thread(target=_loop, daemon=True, name="order-sweeper").start()
