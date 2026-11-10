"""Logs JSON con identificador de correlación y sin credenciales ni datos personales.

Regla: solo se registran metadatos de la solicitud (método, plantilla de ruta, estado,
duración, correlación). No se registran cuerpos, cabeceras, cookies ni query strings.
Cualquier campo extra cuyo nombre parezca sensible se reemplaza por ``[REDACTADO]``.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import time

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")

_SENSITIVE = re.compile(
    r"pass|secret|token|key|auth|cookie|session|phone|telefono|email|correo|address|direccion|run|rut|signature",
    re.I,
)
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "service": self.service,
            "cid": correlation_id.get(),
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in _RESERVED or k.startswith("_"):
                continue
            entry[k] = "[REDACTADO]" if _SENSITIVE.search(k) else v
        if record.exc_info:
            # solo el tipo de excepción: el mensaje puede contener datos
            entry["exc"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging(service: str) -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger(f"lr.{service}")
