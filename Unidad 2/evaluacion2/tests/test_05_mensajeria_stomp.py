"""Mensajería STOMP: Orders publica «pedido_pagado» en /queue/pedidos (misma cola que el material del curso).

Se usa un broker STOMP real en memoria (CoilMQ) levantado por la prueba; en el despliegue es RabbitMQ con el plugin STOMP.
"""
import json
import socket
import threading
import time

import pytest
import stomp
from coilmq.auth.simple import SimpleAuthenticator
from coilmq.queue import QueueManager
from coilmq.scheduler import FavorReliableSubscriberScheduler, RandomQueueScheduler
from coilmq.server.socket_server import ThreadedStompServer
from coilmq.store.memory import MemoryQueue
from coilmq.topic import TopicManager

from conftest import pay_and_decide, place_order, wait_for

PUERTO = 61699
VHOST = socket.getfqdn()  # CoilMQ exige que la cabecera host coincida con el nombre de la máquina


class Buzon(stomp.ConnectionListener):
    def __init__(self, con):
        self.con, self.mensajes = con, []

    def on_message(self, frame):
        self.mensajes.append((dict(frame.headers), frame.body))
        self.con.ack(id=frame.headers.get("ack") or frame.headers["message-id"])


@pytest.fixture(scope="module")
def broker(stack):
    srv = ThreadedStompServer(("127.0.0.1", PUERTO), authenticator=SimpleAuthenticator(store={stack.stomp_user: stack.stomp_password}),
                              queue_manager=QueueManager(store=MemoryQueue(), subscriber_scheduler=FavorReliableSubscriberScheduler(),
                                                         queue_scheduler=RandomQueueScheduler()), topic_manager=TopicManager())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.4)
    stack.stop_service("orders")
    stack.start_service("orders", env={"LR_STOMP_HOST": "127.0.0.1", "LR_STOMP_PORT": str(PUERTO), "LR_STOMP_VHOST": VHOST})
    yield srv
    srv.shutdown()
    srv.server_close()
    stack.stop_service("orders")
    stack.start_service("orders")


def _escuchar(stack):
    con = stomp.Connection12([("127.0.0.1", PUERTO)], vhost=VHOST)
    buzon = Buzon(con)
    con.set_listener("prueba", buzon)
    con.connect(stack.stomp_user, stack.stomp_password, wait=True)
    con.subscribe(destination="/queue/pedidos", id="prueba", ack="client-individual")
    return con, buzon


def test_pedido_pagado_publica_evento_sin_datos_personales(stack, broker, ana):
    """Mensajería · entrada: pago aprobado · identidad: Orders con credencial del broker · esperado: un evento JSON en /queue/pedidos con id, total y líneas, sin datos del cliente · componente: orders + broker STOMP."""
    con, buzon = _escuchar(stack)
    try:
        o = place_order(ana, [{"product_id": "p06", "qty": 2}]).json()
        pay_and_decide(ana, o["id"])
        assert wait_for(lambda: len(buzon.mensajes) >= 1)
        headers, body = buzon.mensajes[0]
        evento = json.loads(body)
        assert headers["x-formato"] == "json" and "application/json" in headers["content-type"]
        assert evento["evento"] == "pedido_pagado" and evento["id"] == o["id"]
        assert evento["total"] == o["total"] and evento["lineas"] == 1 and evento["estado"] == "paid"
        assert set(evento) == {"evento", "id", "estado", "total", "lineas", "fecha"}       # nada más viaja
        assert "ana" not in body.lower() and "u_ana" not in body
        time.sleep(1.0)
        assert len(buzon.mensajes) == 1                                                      # un pago, un evento
    finally:
        con.disconnect()


def test_credencial_incorrecta_es_rechazada_por_el_broker(stack, broker):
    """Mensajería · entrada: conexión con clave errónea · identidad: desconocida · esperado: el broker rechaza la conexión · componente: broker STOMP."""
    con = stomp.Connection12([("127.0.0.1", PUERTO)], vhost=VHOST)
    with pytest.raises(stomp.exception.ConnectFailedException):
        con.connect(stack.stomp_user, "clave-incorrecta", wait=True)


def test_broker_caido_no_afecta_el_pago(stack, ana):
    """Mensajería · entrada: pago aprobado con el broker apagado · identidad: cliente · esperado: el pedido queda pagado igual; solo se pierde el aviso · componente: orders."""
    stack.stop_service("orders")
    stack.start_service("orders", env={"LR_STOMP_HOST": "127.0.0.1", "LR_STOMP_PORT": "61698"})   # nadie escucha ahí
    try:
        o = place_order(ana, [{"product_id": "p06", "qty": 1}]).json()
        pay_and_decide(ana, o["id"])
        assert wait_for(lambda: ana.get(f"/orders/{o['id']}").json()["status"] == "paid")
    finally:
        stack.stop_service("orders")
        stack.start_service("orders")
