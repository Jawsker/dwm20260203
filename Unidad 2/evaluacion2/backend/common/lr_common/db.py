"""Base de datos propia de cada servicio (MongoDB).

Cada servicio abre SOLO su base, con su propio usuario. La cadena de conexión se pide al
gestor de secretos (referencia ``db/<servicio>``), con el formato de connectionstrings.com
para MongoDB: ``mongodb://usuario:clave@host:27017/base?authSource=base``.

``LR_DB_MODE=mock`` usa mongomock (solo para pruebas locales sin Docker: NO persiste).
"""
from __future__ import annotations

import os

from .secrets import secrets


def get_db(service: str):
    if os.getenv("LR_DB_MODE", "mongo") == "mock":
        import mongomock

        return mongomock.MongoClient()[service]
    from pymongo import MongoClient

    uri = secrets.get(f"db/{service}", "uri")
    client = MongoClient(uri, serverSelectionTimeoutMS=int(os.getenv("LR_DB_TIMEOUT_MS", "3000")))
    return client[service]


def db_ping(db) -> bool:
    try:
        db.command("ping")
        return True
    except Exception:  # noqa: BLE001 - cualquier fallo significa "no listo"
        try:  # mongomock no implementa ping en todas las versiones
            db.list_collection_names()
            return True
        except Exception:  # noqa: BLE001
            return False
