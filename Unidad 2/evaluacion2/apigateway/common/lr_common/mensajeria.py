"""Publicación de eventos de pedido en una cola STOMP (misma cola que el material del curso: /queue/pedidos).

* Opcional: si ``LR_STOMP_HOST`` no está definido, no se publica nada y el sistema funciona igual.
* Las credenciales del broker salen del gestor de secretos (referencia ``stomp/broker``), nunca del código.
* Entrega «a lo más una vez»: se publica en segundo plano y, si el broker no responde, el evento se pierde y se
  registra una advertencia. El pedido NUNCA depende del broker (el estado oficial vive en Orders).
* El mensaje no lleva datos personales: solo id de pedido, estado, total y cantidad de líneas.
"""
from __future__ import annotations

import json
import logging
import os
import threading

from .secrets import SecretUnavailable, secrets

DESTINO = "/queue/pedidos"
log = logging.getLogger("lr.mensajeria")


def habilitada() -> bool:
    return bool(os.getenv("LR_STOMP_HOST"))


def _enviar(evento: dict) -> None:
    import stomp  # se importa aquí para que los servicios que no publican no dependan de la librería

    host, port = os.environ["LR_STOMP_HOST"], int(os.getenv("LR_STOMP_PORT", "61613"))
    conexion = stomp.Connection12([(host, port)], vhost=os.getenv("LR_STOMP_VHOST", "/"), timeout=3)
    try:
        conexion.connect(secrets.get("stomp/broker", "user"), secrets.get("stomp/broker", "password"), wait=True)
        conexion.send(destination=DESTINO, body=json.dumps(evento, ensure_ascii=False),
                      headers={"content-type": "application/json; charset=utf-8", "x-formato": "json", "persistent": "true"})
    finally:
        if conexion.is_connected():
            conexion.disconnect()


def publicar(evento: dict) -> None:
    """No bloquea ni lanza: un broker caído no puede hacer fallar un pago."""
    if not habilitada():
        return

    def tarea() -> None:
        try:
            _enviar(evento)
        except SecretUnavailable:
            log.warning("evento_no_publicado", extra={"motivo": "credencial del broker no disponible", "evento": evento.get("evento")})
        except Exception as exc:  # broker caído, credencial rechazada, etc.
            log.warning("evento_no_publicado", extra={"motivo": type(exc).__name__, "evento": evento.get("evento")})

    threading.Thread(target=tarea, daemon=True).start()
