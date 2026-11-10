"""Auth Service (privado).

Custodia credenciales y sesiones. Contraseñas con Argon2id (hash adaptativo con sal propia).
Sesiones: token opaco aleatorio de 256 bits; en la base solo se guarda su SHA-256, de modo
que un volcado de la base no permite suplantar a nadie. Expiran por inactividad y de forma
absoluta, y se revocan al cerrar sesión. El token solo lo ve el gateway, que lo entrega al
navegador como cookie HttpOnly; el JavaScript de la página nunca lo toca.
"""
from __future__ import annotations

import hashlib
import os
import secrets as pysecrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from lr_common.db import db_ping, get_db
from lr_common.web import ApiError, Edge, create_app, edge_guard

SERVICE = "auth"
db = get_db(SERVICE)
ph = PasswordHasher()  # Argon2id, parámetros por defecto de argon2-cffi (RFC 9106 perfil bajo)
DUMMY_HASH = ph.hash("contraseña-ficticia-para-igualar-tiempos")

IDLE = int(os.getenv("LR_SESSION_IDLE_SECONDS", "1800"))
ABSOLUTE = int(os.getenv("LR_SESSION_ABSOLUTE_SECONDS", "28800"))
MAX_FAILS = int(os.getenv("LR_LOGIN_MAX_FAILS", "5"))
LOCK_SECONDS = int(os.getenv("LR_LOGIN_LOCK_SECONDS", "900"))

app = create_app(SERVICE, ready_checks={"db": lambda: db_ping(db)})
guard = edge_guard(SERVICE, allowed=["gateway"], identity_from=["gateway"])


def now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_indexes() -> None:
    db.users.create_index("email", unique=True)
    db.sessions.create_index("user_id")


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10, max_length=128)


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class Introspect(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class StaffUser(Credentials):
    role: str = Field(pattern=r"^(staff|auditor|admin)$")


def _create_user(email: str, password: str, role: str, user_id: Optional[str] = None) -> dict:
    doc = {
        "_id": user_id or f"u_{uuid.uuid4().hex[:12]}",
        "email": email.strip().lower(),
        "pw_hash": ph.hash(password),
        "role": role,
        "status": "active",
        "failed_attempts": 0,
        "locked_until": None,
        "created_at": now(),
    }
    try:
        db.users.insert_one(doc)
    except DuplicateKeyError:
        raise ApiError(409, "email_taken", "Ya existe una cuenta con ese correo.")
    return doc


@app.post("/internal/register", status_code=201)
def register(body: Credentials, edge: Edge = Depends(guard)):
    # El rol NO viene del cliente: el registro público siempre crea "customer".
    doc = _create_user(body.email, body.password, "customer")
    return {"user_id": doc["_id"], "role": doc["role"]}


@app.post("/internal/users", status_code=201)
def create_staff(body: StaffUser, edge: Edge = Depends(guard)):
    edge.need_identity().require("admin")
    doc = _create_user(body.email, body.password, body.role)
    return {"user_id": doc["_id"], "role": doc["role"]}


@app.delete("/internal/users/{user_id}", status_code=204)
def delete_user(user_id: str, edge: Edge = Depends(guard)):
    """Eliminación de cuenta (propia) o compensación de un registro fallido."""
    ident = edge.need_identity() if edge.identity else None
    if ident is not None and ident.user_id != user_id and ident.role != "admin":
        raise ApiError(403, "forbidden", "Solo puedes eliminar tu propia cuenta.")
    db.sessions.delete_many({"user_id": user_id})
    db.users.delete_one({"_id": user_id})
    return None


@app.post("/internal/login")
def login(body: Login, edge: Edge = Depends(guard)):
    email = body.email.strip().lower()
    user = db.users.find_one({"email": email})
    t = now()
    locked = user and user.get("locked_until") and user["locked_until"].replace(tzinfo=timezone.utc) > t
    if locked:
        raise ApiError(429, "too_many_attempts", "Cuenta bloqueada temporalmente por intentos fallidos.")
    ok = False
    if user and user["status"] == "active":
        try:
            ok = ph.verify(user["pw_hash"], body.password)
        except (VerifyMismatchError, InvalidHashError):
            ok = False
    else:  # igualar el tiempo de respuesta para no revelar si el correo existe
        try:
            ph.verify(DUMMY_HASH, body.password)
        except VerifyMismatchError:
            pass
    if not ok:
        if user:
            fails = user.get("failed_attempts", 0) + 1
            patch = {"failed_attempts": fails}
            if fails >= MAX_FAILS:
                patch.update(failed_attempts=0, locked_until=t + timedelta(seconds=LOCK_SECONDS))
            db.users.update_one({"_id": user["_id"]}, {"$set": patch})
        raise ApiError(401, "invalid_credentials", "Correo o contraseña incorrectos.")
    db.users.update_one({"_id": user["_id"]}, {"$set": {"failed_attempts": 0, "locked_until": None}})
    if ph.check_needs_rehash(user["pw_hash"]):
        db.users.update_one({"_id": user["_id"]}, {"$set": {"pw_hash": ph.hash(body.password)}})
    token = pysecrets.token_urlsafe(32)
    db.sessions.insert_one({
        "_id": _hash_token(token), "user_id": user["_id"], "role": user["role"],
        "created_at": t, "last_seen": t, "expires_at": t + timedelta(seconds=ABSOLUTE),
    })
    return {"token": token, "max_age": ABSOLUTE,
            "user": {"id": user["_id"], "email": user["email"], "role": user["role"]}}


@app.post("/internal/introspect")
def introspect(body: Introspect, edge: Edge = Depends(guard)):
    key = _hash_token(body.token)
    s = db.sessions.find_one({"_id": key})
    if not s:
        return {"active": False}
    t = now()
    last = s["last_seen"].replace(tzinfo=timezone.utc)
    exp = s["expires_at"].replace(tzinfo=timezone.utc)
    if t > exp or (t - last).total_seconds() > IDLE:
        db.sessions.delete_one({"_id": key})
        return {"active": False}
    user = db.users.find_one({"_id": s["user_id"]})
    if not user or user["status"] != "active":
        db.sessions.delete_one({"_id": key})
        return {"active": False}
    db.sessions.update_one({"_id": key}, {"$set": {"last_seen": t}})
    # El rol se lee del usuario (no de la sesión): un cambio de rol surte efecto de inmediato.
    return {"active": True, "user_id": user["_id"], "role": user["role"], "email": user["email"]}


@app.post("/internal/logout", status_code=204)
def logout(body: Introspect, edge: Edge = Depends(guard)):
    db.sessions.delete_one({"_id": _hash_token(body.token)})
    return None


# ---------------------------------------------------------------- datos de prueba
SEED_USERS = [
    ("u_ana", "ana@ejemplo.cl", "customer"),
    ("u_beto", "beto@ejemplo.cl", "customer"),
    ("u_staff", "tienda@libreyrico.test", "staff"),
    ("u_admin", "admin@libreyrico.test", "admin"),
    ("u_audit", "auditoria@libreyrico.test", "auditor"),
]


def seed() -> None:
    """Usuarios FICTICIOS. La contraseña viene de LR_SEED_PASSWORD (no está en el repositorio)."""
    password = os.getenv("LR_SEED_PASSWORD")
    if not password or len(password) < 10:
        raise SystemExit("Define LR_SEED_PASSWORD (mínimo 10 caracteres) para crear los usuarios de prueba.")
    for uid, email, role in SEED_USERS:
        if not db.users.find_one({"_id": uid}):
            _create_user(email, password, role, user_id=uid)


ensure_indexes()
if os.getenv("LR_SEED") == "1":
    seed()

if __name__ == "__main__":
    seed()
    print("usuarios de prueba creados")
