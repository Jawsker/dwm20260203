"""Clients Service (privado). Dueño de los datos personales del cliente y de los mensajes de contacto.

Regla de acceso a registros: un cliente solo ve y modifica SU perfil (el id sale de la identidad
verificada, nunca de un parámetro). Personal de tienda ve nombre y teléfono para coordinar retiros;
administración ve además dirección; auditoría no accede a datos personales.
No custodia secretos del cliente (contraseñas viven en Auth; datos de tarjeta nunca llegan aquí).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from lr_common.db import db_ping, get_db
from lr_common.web import ApiError, Edge, create_app, edge_guard

SERVICE = "clients"
db = get_db(SERVICE)
app = create_app(SERVICE, ready_checks={"db": lambda: db_ping(db)})
guard = edge_guard(SERVICE, allowed=["gateway", "graphql"], identity_from=["gateway", "graphql"])

VISIBLE = {  # campos que devuelve el servicio según el rol del solicitante
    "self": ("id", "nombre", "telefono", "direccion"),
    "staff": ("id", "nombre", "telefono"),
    "admin": ("id", "nombre", "telefono", "direccion"),
    "auditor": (),
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def public_view(doc: dict, mode: str) -> dict:
    out = {"id": doc["_id"], "nombre": doc.get("nombre"), "telefono": doc.get("telefono"), "direccion": doc.get("direccion")}
    return {k: out[k] for k in VISIBLE[mode]}


def mode_for(ident, target_id: str) -> str:
    if ident.user_id == target_id and ident.role == "customer":
        return "self"
    if ident.role in ("staff", "admin"):
        return ident.role
    if ident.role == "auditor":
        raise ApiError(403, "forbidden", "Auditoría no accede a datos personales.")
    raise ApiError(404, "not_found", "Cliente no encontrado.")  # un cliente no distingue ajenos de inexistentes


class NewProfile(BaseModel):
    user_id: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=2, max_length=80)
    telefono: Optional[str] = Field(default=None, pattern=r"^\+?[0-9 ]{8,15}$")


class ProfilePatch(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=80)
    telefono: Optional[str] = Field(default=None, pattern=r"^\+?[0-9 ]{8,15}$")
    direccion: Optional[str] = Field(default=None, min_length=5, max_length=160)


class Batch(BaseModel):
    ids: list[str] = Field(max_length=50)


class Contact(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    correo: str = Field(max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    mensaje: str = Field(min_length=5, max_length=1000)


@app.post("/internal/clients", status_code=201)
def create_profile(body: NewProfile, edge: Edge = Depends(guard)):
    doc = {"_id": body.user_id, "nombre": body.nombre, "telefono": body.telefono, "direccion": None, "created_at": now()}
    try:
        db.clients.insert_one(doc)
    except DuplicateKeyError:
        raise ApiError(409, "profile_exists", "El perfil ya existe.")
    return public_view(doc, "self")


@app.get("/internal/clients/me")
def my_profile(edge: Edge = Depends(guard)):
    ident = edge.need_identity().require("customer")
    doc = db.clients.find_one({"_id": ident.user_id})
    if not doc:
        raise ApiError(404, "not_found", "Aún no tienes perfil.")
    return public_view(doc, "self")


@app.put("/internal/clients/me")
def update_profile(body: ProfilePatch, edge: Edge = Depends(guard)):
    ident = edge.need_identity().require("customer")
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise ApiError(400, "empty_update", "No hay cambios que aplicar.")
    patch["updated_at"] = now()
    res = db.clients.update_one({"_id": ident.user_id}, {"$set": patch})
    if res.matched_count == 0:
        raise ApiError(404, "not_found", "Aún no tienes perfil.")
    return public_view(db.clients.find_one({"_id": ident.user_id}), "self")


@app.delete("/internal/clients/me", status_code=204)
def delete_profile(edge: Edge = Depends(guard)):
    """Eliminación de datos personales a solicitud del titular."""
    ident = edge.need_identity().require("customer")
    db.clients.delete_one({"_id": ident.user_id})
    return None


@app.get("/internal/clients/{client_id}")
def get_client(client_id: str, edge: Edge = Depends(guard)):
    ident = edge.need_identity()
    mode = mode_for(ident, client_id)
    doc = db.clients.find_one({"_id": client_id})
    if not doc:
        raise ApiError(404, "not_found", "Cliente no encontrado.")
    return public_view(doc, mode)


@app.post("/internal/clients/batch")
def batch(body: Batch, edge: Edge = Depends(guard)):
    """Una sola consulta para muchos clientes (evita N+1 desde GraphQL). Solo personal autorizado."""
    ident = edge.need_identity().require("staff", "admin")
    docs = db.clients.find({"_id": {"$in": body.ids}})
    return {"items": [public_view(d, ident.role) for d in docs]}


@app.post("/internal/contact", status_code=201)
def contact(body: Contact, edge: Edge = Depends(guard)):
    doc = {"_id": uuid.uuid4().hex[:12], **body.model_dump(), "created_at": now(), "status": "nuevo"}
    db.contact_messages.insert_one(doc)
    return {"id": doc["_id"], "status": "nuevo"}


@app.get("/internal/contact")
def list_contact(limit: int = 20, edge: Edge = Depends(guard)):
    edge.need_identity().require("staff", "admin")
    limit = max(1, min(limit, 50))
    rows = db.contact_messages.find().sort("created_at", -1).limit(limit)
    return {"items": [{"id": r["_id"], "nombre": r["nombre"], "correo": r["correo"], "mensaje": r["mensaje"],
                       "status": r["status"], "created_at": r["created_at"].replace(tzinfo=None).isoformat(timespec="seconds") + "Z"} for r in rows]}


SEED = [
    ("u_ana", "Ana Pérez (ficticia)", "+56 9 1111 2222", "Av. Ejemplo 123, Santiago"),
    ("u_beto", "Beto Soto (ficticio)", "+56 9 3333 4444", "Calle Falsa 456, Viña del Mar"),
]


def seed() -> None:
    for uid, nombre, tel, dire in SEED:
        if not db.clients.find_one({"_id": uid}):
            db.clients.insert_one({"_id": uid, "nombre": nombre, "telefono": tel, "direccion": dire, "created_at": now()})


if os.getenv("LR_SEED") == "1":
    seed()
