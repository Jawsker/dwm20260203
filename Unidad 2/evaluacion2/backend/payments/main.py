"""Payments Service (privado). Dueño de las intenciones de pago y de la verificación del proveedor.

Proveedor: ADAPTADOR SANDBOX propio (no hay cuenta real del proveedor en este entorno). Preserva el
contrato de un proveedor real: el resultado llega por webhook firmado (HMAC-SHA256 con marca de
tiempo), con ``event_id`` único. Lo que el navegador envíe jamás confirma un pago: el único camino a
``paid`` es webhook verificado -> Payments -> Orders (que además re-verifica el monto).

Para cambiar a un proveedor real basta reemplazar ``sandbox_decide`` (simulación) por la creación de
la sesión de pago del proveedor; el webhook y las reglas de idempotencia no cambian.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets as pysecrets
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from lr_common.client import ServiceClient
from lr_common.db import db_ping, get_db
from lr_common.secrets import SecretUnavailable, secrets
from lr_common.web import ApiError, Edge, create_app, edge_guard

SERVICE = "payments"
db = get_db(SERVICE)
app = create_app(SERVICE, ready_checks={"db": lambda: db_ping(db)})
guard = edge_guard(SERVICE, allowed=["gateway", "orders"], identity_from=["gateway"])
orders = ServiceClient(SERVICE, "orders", "LR_ORDERS_URL", "http://orders:8000", timeout=4.0)
TOLERANCE = int(os.getenv("LR_WEBHOOK_TOLERANCE_SECONDS", "300"))


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sign(secret: str, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"


def verify_signature(secret: str, header: str, body: bytes) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        ts, given = int(parts["t"]), parts["v1"]
    except (ValueError, KeyError):
        return False
    if abs(time.time() - ts) > TOLERANCE:  # anti-repetición: eventos viejos se rechazan
        return False
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, given)


class NewPayment(BaseModel):
    order_id: str = Field(max_length=40)
    user_id: str = Field(max_length=40)
    amount: int = Field(gt=0, le=10_000_000)


class Decision(BaseModel):
    outcome: str = Field(pattern=r"^(approve|reject)$")


class ProviderEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    type: str = Field(pattern=r"^payment\.(succeeded|failed)$")
    provider_ref: str = Field(max_length=80)
    amount: int = Field(ge=0)


@app.post("/internal/payments", status_code=201)
def create_payment(body: NewPayment, edge: Edge = Depends(guard)):
    if edge.caller != "orders":
        raise ApiError(403, "forbidden", "Solo Orders crea intenciones de pago.")
    if db.payments.find_one({"order_id": body.order_id, "status": "succeeded"}):
        raise ApiError(409, "already_paid", "El pedido ya tiene un pago exitoso.")
    pending = db.payments.find_one({"order_id": body.order_id, "status": "pending"})
    if pending:  # doble clic / reintento: se reutiliza la intención abierta
        return {"payment_id": pending["_id"], "provider_ref": pending["provider_ref"], "status": "pending"}
    doc = {"_id": "pay_" + pysecrets.token_hex(8), "order_id": body.order_id, "user_id": body.user_id,
           "amount": body.amount, "currency": "CLP", "status": "pending",
           "provider_ref": "sbx_" + pysecrets.token_urlsafe(16), "created_at": now()}
    db.payments.insert_one(doc)
    return {"payment_id": doc["_id"], "provider_ref": doc["provider_ref"], "status": "pending"}


@app.get("/internal/payments/by-ref/{provider_ref}")
def payment_by_ref(provider_ref: str, edge: Edge = Depends(guard)):
    ident = edge.need_identity()
    p = db.payments.find_one({"provider_ref": provider_ref})
    if not p or (ident.role == "customer" and p["user_id"] != ident.user_id):
        raise ApiError(404, "not_found", "Pago no encontrado.")
    return {"payment_id": p["_id"], "order_id": p["order_id"], "amount": p["amount"], "currency": p["currency"],
            "status": p["status"]}


@app.post("/internal/sandbox/{provider_ref}/decide")
def sandbox_decide(provider_ref: str, body: Decision, edge: Edge = Depends(guard)):
    """Simula al proveedor: el usuario "aprueba/rechaza" en la pantalla del proveedor.

    El navegador solo indica el resultado de ESA pantalla simulada; el pedido cambia de estado
    únicamente cuando el evento firmado llega al webhook y se verifica.
    """
    ident = edge.need_identity().require("customer")
    p = db.payments.find_one({"provider_ref": provider_ref})
    if not p or p["user_id"] != ident.user_id:
        raise ApiError(404, "not_found", "Pago no encontrado.")
    if p["status"] != "pending":
        raise ApiError(409, "invalid_state", "Este pago ya fue resuelto.")
    event = {"event_id": "evt_" + pysecrets.token_hex(8),
             "type": "payment.succeeded" if body.outcome == "approve" else "payment.failed",
             "provider_ref": provider_ref, "amount": p["amount"]}
    raw = json.dumps(event, separators=(",", ":")).encode()
    try:
        secret = secrets.get("payments/webhook", "secret")
    except SecretUnavailable as exc:
        raise ApiError(503, "secrets_unavailable", "Gestor de secretos no disponible.") from exc
    url = os.getenv("LR_WEBHOOK_URL", "http://gateway:8000/api/v1/webhooks/payments")
    try:
        r = httpx.post(url, content=raw, timeout=6,
                       headers={"Content-Type": "application/json", "X-Provider-Signature": sign(secret, int(time.time()), raw)})
    except httpx.HTTPError as exc:
        raise ApiError(502, "webhook_delivery_failed", "El proveedor no pudo notificar el resultado.") from exc
    return {"event_id": event["event_id"], "webhook_status": r.status_code}


@app.post("/internal/webhooks/provider")
async def provider_webhook(request: Request, edge: Edge = Depends(guard)):
    raw = await request.body()
    return await run_in_threadpool(_process_webhook, raw, request.headers.get("x-provider-signature", ""))


def _process_webhook(raw: bytes, signature: str):
    try:
        secret = secrets.get("payments/webhook", "secret")
    except SecretUnavailable as exc:
        raise ApiError(503, "secrets_unavailable", "Gestor de secretos no disponible.") from exc
    if not verify_signature(secret, signature, raw):
        raise ApiError(401, "invalid_signature", "Firma del webhook inválida o vencida.")
    try:
        event = ProviderEvent.model_validate_json(raw)
    except ValueError:
        raise ApiError(400, "validation_error", "Evento mal formado.")

    try:
        db.webhook_events.insert_one({"_id": event.event_id, "status": "received", "type": event.type, "at": now()})
    except DuplicateKeyError:
        prev = db.webhook_events.find_one({"_id": event.event_id})
        if prev["status"] in ("processed", "rejected"):  # idempotencia: mismo evento, sin efectos nuevos
            return {"duplicate": True}
        # estado "received": el intento anterior no terminó; se reprocesa

    p = db.payments.find_one({"provider_ref": event.provider_ref})
    if not p:
        db.webhook_events.update_one({"_id": event.event_id}, {"$set": {"status": "processed", "note": "unknown_payment"}})
        return {"ignored": True}
    if event.amount != p["amount"]:
        db.webhook_events.update_one({"_id": event.event_id}, {"$set": {"status": "rejected", "note": "amount_mismatch"}})
        app.state.log.warning("webhook_monto_inconsistente", extra={"payment": p["_id"]})
        raise ApiError(400, "amount_mismatch", "El monto del evento no coincide con la intención de pago.")

    new_status = "succeeded" if event.type == "payment.succeeded" else "failed"
    if p["status"] == "succeeded":  # un pago exitoso no se revierte ni se repite
        db.webhook_events.update_one({"_id": event.event_id}, {"$set": {"status": "processed", "note": "already_succeeded"}})
        return {"duplicate_payment": True}
    db.payments.update_one({"_id": p["_id"]}, {"$set": {"status": new_status, "resolved_at": now()}})
    try:
        orders.call("POST", f"/internal/orders/{p['order_id']}/payment-result",
                    json={"payment_id": p["_id"], "status": new_status, "amount": p["amount"], "event_id": event.event_id})
    except ApiError as exc:
        if exc.status in (400, 409):  # Orders rechazó el pago por inconsistencia: no reintentar
            db.webhook_events.update_one({"_id": event.event_id}, {"$set": {"status": "rejected", "note": exc.code}})
            raise
        # Orders no disponible: responder error para que el proveedor reintente el mismo evento.
        db.payments.update_one({"_id": p["_id"], "status": new_status}, {"$set": {"status": "pending", "notify_pending": True}})
        raise
    db.webhook_events.update_one({"_id": event.event_id}, {"$set": {"status": "processed"}})
    return {"processed": True}


db.payments.create_index("provider_ref", unique=True)
db.payments.create_index("order_id")
