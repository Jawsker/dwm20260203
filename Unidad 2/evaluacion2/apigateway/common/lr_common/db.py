"""Base de datos propia de cada servicio (MongoDB).

Cada servicio abre SOLO su base, con su propio usuario. La cadena de conexión se pide al
gestor de secretos (referencia ``db/<servicio>``), con el formato de connectionstrings.com
para MongoDB: ``mongodb://usuario:clave@host:27017/base?authSource=base``.

``LR_DB_MODE=mock`` usa mongomock (solo para pruebas locales sin Docker: NO persiste).
"""
from __future__ import annotations

import os

from .secrets import secrets


_IGNORAR = {"ping", "hello", "ismaster", "endsessions", "saslstart", "saslcontinue", "buildinfo", "getnonce", "killcursors"}
_VERBOS = {"find": "consulta", "aggregate": "agregación", "count": "conteo", "insert": "inserción",
           "update": "modificación", "delete": "eliminación", "findandmodify": "modificación", "createindexes": "índices"}


def _registro_mongo_cls():
    from pymongo import monitoring

    class RegistroMongo(monitoring.CommandListener):
        """Escribe en el log cada operación real contra MongoDB (colección y tipo), sin el contenido."""

        def started(self, event):
            nombre = event.command_name.lower()
            if nombre in _IGNORAR:
                return
            from .logs import correlation_id
            if correlation_id.get() == "-":  # tareas de fondo (barrido de pedidos vencidos): no ensuciar el log
                return
            coleccion = event.command.get(event.command_name)
            from .logs import paso
            paso(f"MongoDB {event.database_name}.{coleccion}: {_VERBOS.get(nombre, nombre)} ({event.command_name})",
                 base=event.database_name, coleccion=coleccion, operacion=event.command_name)

        def succeeded(self, event):
            pass

        def failed(self, event):
            from .logs import paso
            paso(f"MongoDB {event.database_name}: {event.command_name} FALLÓ", 30, operacion=event.command_name)

    return RegistroMongo


def _RegistroMongo():
    return _registro_mongo_cls()()


def get_db(service: str):
    if os.getenv("LR_DB_MODE", "mongo") == "mock":
        import mongomock

        return mongomock.MongoClient()[service]
    from pymongo import MongoClient

    uri = secrets.get(f"db/{service}", "uri")
    client = MongoClient(uri, serverSelectionTimeoutMS=int(os.getenv("LR_DB_TIMEOUT_MS", "3000")),
                         event_listeners=[_RegistroMongo()])
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
