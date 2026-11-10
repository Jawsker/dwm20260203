"""Inventory Service (privado). Dueño del catálogo y del stock.

Modelo de stock por producto: ``stock`` (físico), ``reserved`` (comprometido en pedidos
pendientes) y ``available`` (= stock - reserved). Reservar es una actualización condicional
atómica ``available >= cantidad``: dos compradores simultáneos no pueden quedarse con la
misma última unidad. La reserva de un pedido es todo-o-nada y se identifica por order_id,
así que repetir la llamada (reintento de red) no reserva dos veces.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from lr_common.db import db_ping, get_db
from lr_common.web import ApiError, Edge, create_app, edge_guard

SERVICE = "inventory"
db = get_db(SERVICE)
app = create_app(SERVICE, ready_checks={"db": lambda: db_ping(db)})
guard = edge_guard(SERVICE, allowed=["gateway", "orders", "graphql"], identity_from=["gateway", "graphql"])
CATEGORIAS = ("panes", "pasteleria", "galletas", "salados")
LOW_STOCK = int(os.getenv("LR_LOW_STOCK", "5"))


def now() -> datetime:
    return datetime.now(timezone.utc)


def catalog_view(p: dict) -> dict:
    """Campos del catálogo (públicos). El stock exacto NO sale por aquí."""
    return {"id": p["_id"], "categoria": p["categoria"], "emoji": p.get("emoji", ""), "nombre": p["nombre"],
            "descripcion": p["descripcion"], "precio": p["precio"], "disponible": p["available"] > 0}


def staff_view(p: dict) -> dict:
    return {**catalog_view(p), "stock": p["stock"], "reservado": p["reserved"], "disponible_unidades": p["available"],
            "activo": p["active"]}


class ProductIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]{3,40}$")
    categoria: str = Field(pattern=r"^(panes|pasteleria|galletas|salados)$")
    emoji: str = Field(default="", max_length=8)
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str = Field(min_length=5, max_length=300)
    precio: int = Field(gt=0, le=1_000_000)
    stock: int = Field(ge=0, le=100_000)


class ProductPatch(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=80)
    descripcion: Optional[str] = Field(default=None, min_length=5, max_length=300)
    precio: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    active: Optional[bool] = None


class StockIn(BaseModel):
    stock: int = Field(ge=0, le=100_000)


class Item(BaseModel):
    product_id: str = Field(max_length=40)
    qty: int = Field(ge=1, le=20)


class Reserve(BaseModel):
    order_id: str = Field(max_length=40)
    items: list[Item] = Field(min_length=1, max_length=30)


class Ids(BaseModel):
    ids: list[str] = Field(max_length=100)


@app.get("/internal/products")
def list_products(categoria: Optional[str] = None, q: Optional[str] = None, available: Optional[bool] = None,
                  limit: int = 50, offset: int = 0, edge: Edge = Depends(guard)):
    if categoria and categoria not in CATEGORIAS:
        raise ApiError(400, "invalid_filter", "Categoría desconocida.")
    if q and len(q) > 60:
        raise ApiError(400, "invalid_filter", "Búsqueda demasiado larga.")
    if not 1 <= limit <= 100 or offset < 0:
        raise ApiError(400, "invalid_filter", "Paginación fuera de rango.")
    flt: dict = {"active": True}
    if categoria:
        flt["categoria"] = categoria
    if available is True:
        flt["available"] = {"$gt": 0}
    rows = [p for p in db.products.find(flt).sort("_id", 1)]
    if q:  # búsqueda literal (no regex del usuario)
        needle = q.lower()
        rows = [p for p in rows if needle in p["nombre"].lower() or needle in p["descripcion"].lower()]
    total = len(rows)
    page = rows[offset:offset + limit]
    staff = edge.identity is not None and edge.identity.role in ("staff", "admin")
    return {"items": [staff_view(p) if staff else catalog_view(p) for p in page], "total": total,
            "categorias": list(CATEGORIAS)}


@app.post("/internal/products/batch")
def products_batch(body: Ids, edge: Edge = Depends(guard)):
    rows = db.products.find({"_id": {"$in": body.ids}})
    return {"items": [catalog_view(p) for p in rows]}


@app.get("/internal/products/low-stock")
def low_stock(edge: Edge = Depends(guard)):
    edge.need_identity().require("staff", "admin")
    rows = db.products.find({"active": True, "available": {"$lte": LOW_STOCK}}).sort("available", 1)
    return {"items": [staff_view(p) for p in rows], "umbral": LOW_STOCK}


@app.get("/internal/products/{product_id}")
def get_product(product_id: str, edge: Edge = Depends(guard)):
    p = db.products.find_one({"_id": product_id, "active": True})
    if not p:
        raise ApiError(404, "not_found", "Producto no encontrado.")
    return catalog_view(p)


@app.post("/internal/products", status_code=201)
def create_product(body: ProductIn, edge: Edge = Depends(guard)):
    edge.need_identity().require("admin")
    doc = {"_id": body.id, **body.model_dump(exclude={"id", "stock"}), "stock": body.stock, "reserved": 0,
           "available": body.stock, "active": True, "created_at": now()}
    try:
        db.products.insert_one(doc)
    except DuplicateKeyError:
        raise ApiError(409, "product_exists", "Ya existe un producto con ese id.")
    return staff_view(doc)


@app.put("/internal/products/{product_id}")
def update_product(product_id: str, body: ProductPatch, edge: Edge = Depends(guard)):
    edge.need_identity().require("admin")
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise ApiError(400, "empty_update", "No hay cambios que aplicar.")
    # El precio nuevo rige para pedidos futuros; los pedidos ya creados conservan su precio.
    res = db.products.update_one({"_id": product_id}, {"$set": patch})
    if res.matched_count == 0:
        raise ApiError(404, "not_found", "Producto no encontrado.")
    return staff_view(db.products.find_one({"_id": product_id}))


@app.put("/internal/products/{product_id}/stock")
def set_stock(product_id: str, body: StockIn, edge: Edge = Depends(guard)):
    edge.need_identity().require("staff", "admin")
    p = db.products.find_one({"_id": product_id})
    if not p:
        raise ApiError(404, "not_found", "Producto no encontrado.")
    if body.stock < p["reserved"]:
        raise ApiError(409, "stock_below_reserved", "El stock no puede ser menor que lo ya reservado.")
    delta = body.stock - p["stock"]
    db.products.update_one({"_id": product_id}, {"$set": {"stock": body.stock}, "$inc": {"available": delta}})
    return staff_view(db.products.find_one({"_id": product_id}))


# ------------------------------------------------------------------ reservas (solo orders)
def _only_orders(edge: Edge) -> None:
    if edge.caller != "orders":
        raise ApiError(403, "forbidden", "Operación reservada al servicio de pedidos.")


@app.post("/internal/reservations", status_code=201)
def reserve(body: Reserve, edge: Edge = Depends(guard)):
    _only_orders(edge)
    existing = db.reservations.find_one({"_id": body.order_id})
    if existing:  # idempotente: mismo pedido, misma reserva
        return {"order_id": body.order_id, "status": existing["status"], "replayed": True}
    merged: dict[str, int] = {}
    for it in body.items:
        merged[it.product_id] = merged.get(it.product_id, 0) + it.qty
    done: list[tuple[str, int]] = []
    for pid, qty in merged.items():
        res = db.products.update_one({"_id": pid, "active": True, "available": {"$gte": qty}},
                                     {"$inc": {"available": -qty, "reserved": qty}})
        if res.modified_count != 1:
            for rp, rq in done:  # compensación: todo o nada
                db.products.update_one({"_id": rp}, {"$inc": {"available": rq, "reserved": -rq}})
            p = db.products.find_one({"_id": pid})
            if not p or not p.get("active"):
                raise ApiError(409, "product_unavailable", "Un producto ya no está disponible.", [{"product_id": pid}])
            raise ApiError(409, "insufficient_stock", "No hay stock suficiente.",
                           [{"product_id": pid, "solicitado": qty, "disponible": p["available"]}])
        done.append((pid, qty))
    try:
        db.reservations.insert_one({"_id": body.order_id, "items": merged, "status": "active", "created_at": now()})
    except DuplicateKeyError:  # carrera con un reintento simultáneo: deshacer lo recién descontado
        for rp, rq in done:
            db.products.update_one({"_id": rp}, {"$inc": {"available": rq, "reserved": -rq}})
        return {"order_id": body.order_id, "status": "active", "replayed": True}
    return {"order_id": body.order_id, "status": "active", "replayed": False}


def _finish(order_id: str, to: str) -> dict:
    # La transición active -> (released|committed) ocurre una sola vez gracias al filtro por estado.
    res = db.reservations.find_one_and_update({"_id": order_id, "status": "active"}, {"$set": {"status": to, "closed_at": now()}})
    if res is None:
        cur = db.reservations.find_one({"_id": order_id})
        if cur is None:
            raise ApiError(404, "not_found", "Reserva inexistente.")
        return {"order_id": order_id, "status": cur["status"], "replayed": True}
    for pid, qty in res["items"].items():
        if to == "released":
            db.products.update_one({"_id": pid}, {"$inc": {"available": qty, "reserved": -qty}})
        else:  # committed: el producto sale físicamente
            db.products.update_one({"_id": pid}, {"$inc": {"reserved": -qty, "stock": -qty}})
    return {"order_id": order_id, "status": to, "replayed": False}


@app.post("/internal/reservations/{order_id}/release")
def release(order_id: str, edge: Edge = Depends(guard)):
    _only_orders(edge)
    return _finish(order_id, "released")


@app.post("/internal/reservations/{order_id}/commit")
def commit(order_id: str, edge: Edge = Depends(guard)):
    _only_orders(edge)
    return _finish(order_id, "committed")


@app.get("/internal/reservations/{order_id}")
def get_reservation(order_id: str, edge: Edge = Depends(guard)):
    _only_orders(edge)
    r = db.reservations.find_one({"_id": order_id})
    if not r:
        raise ApiError(404, "not_found", "Reserva inexistente.")
    return {"order_id": order_id, "status": r["status"], "items": r["items"]}


def seed() -> None:
    path = Path(os.getenv("LR_CATALOG_FILE", Path(__file__).parent / "catalogo.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    stock_inicial = int(os.getenv("LR_SEED_STOCK", "20"))
    for p in data["productos"]:
        pid = f"p{int(p['id']):02d}"  # el JSON histórico usa enteros; el servicio usa ids de texto
        if not db.products.find_one({"_id": pid}):
            db.products.insert_one({"_id": pid, "categoria": p["categoria"], "emoji": p.get("emoji", ""),
                                    "nombre": p["nombre"], "descripcion": p["descripcion"], "precio": int(p["precio"]),
                                    "stock": stock_inicial, "reserved": 0, "available": stock_inicial,
                                    "active": True, "created_at": now()})


db.products.create_index("categoria")
if os.getenv("LR_SEED") == "1":
    seed()
