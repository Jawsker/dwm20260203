#!/usr/bin/env python3
"""Consumidor STOMP: escucha /queue/pedidos y avisa a la tienda de cada pedido pagado.

Representa el aviso interno «hay un pedido nuevo para preparar». No decide nada: el estado oficial del
pedido vive en Orders; si este proceso no está corriendo, el sistema sigue funcionando.

  export STOMP_USUARIO=...  STOMP_CLAVE=...
  python consumidor.py
"""
import argparse
import json
import os
import time
import xml.etree.ElementTree as ET

import stomp

DESTINO = "/queue/pedidos"
CAMPOS = {"evento", "id", "estado", "total", "lineas", "fecha"}


def interpretar(cuerpo: str, headers: dict) -> dict:
    formato = headers.get("x-formato", "").lower()
    tipo_mime = headers.get("content-type", "").lower()
    if not formato:
        formato = "json" if "application/json" in tipo_mime else "xml" if "xml" in tipo_mime else ""
    if formato == "json":
        datos = json.loads(cuerpo)
    elif formato == "xml":
        raiz = ET.fromstring(cuerpo)
        if raiz.tag != "pedido":
            raise ValueError("El nodo raíz de XML debe ser <pedido>")
        datos = {e.tag: e.text for e in raiz}
    else:
        raise ValueError(f"Formato no soportado: {formato or tipo_mime}")
    if not isinstance(datos, dict) or not {"evento", "id", "total"} <= set(datos):
        raise ValueError("Faltan campos obligatorios (evento, id, total)")
    return {k: v for k, v in datos.items() if k in CAMPOS}  # se ignoran campos no esperados


class Escuchador(stomp.ConnectionListener):
    def __init__(self, conexion):
        self.conexion = conexion

    def on_error(self, frame):
        print(f"ERROR del broker: {frame.body}")

    def on_disconnected(self):
        print("Conexión STOMP cerrada")

    def on_message(self, frame):
        ack_id = frame.headers.get("ack") or frame.headers.get("message-id")
        try:
            evento = interpretar(frame.body, frame.headers)
            print(f"\n[PEDIDO PARA PREPARAR] {evento['id']} · total ${evento['total']} · {evento.get('lineas', '?')} línea(s)")
            print(json.dumps(evento, ensure_ascii=False, indent=2))
            self.conexion.ack(id=ack_id)
        except Exception as exc:
            print(f"[MENSAJE NO VÁLIDO] {exc}")
            self.conexion.nack(id=ack_id, requeue="false")


def main():
    parser = argparse.ArgumentParser(description="Consumidor STOMP de eventos de pedido (Libre & Rico)")
    parser.add_argument("--host", default=os.getenv("LR_STOMP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("LR_STOMP_PORT", "61613")))
    parser.add_argument("--vhost", default=os.getenv("LR_STOMP_VHOST", "/"))
    args = parser.parse_args()
    usuario, clave = os.getenv("STOMP_USUARIO"), os.getenv("STOMP_CLAVE")
    if not usuario or not clave:
        parser.error("Define STOMP_USUARIO y STOMP_CLAVE en el entorno.")
    conexion = stomp.Connection12([(args.host, args.port)], vhost=args.vhost)
    conexion.set_listener("pedidos", Escuchador(conexion))
    try:
        conexion.connect(usuario, clave, wait=True)
        conexion.subscribe(destination=DESTINO, id="lector-pedidos", ack="client-individual", headers={"prefetch-count": "1"})
        print(f"Escuchando {DESTINO}. Presiona Ctrl+C para salir.")
        while conexion.is_connected():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nDeteniendo consumidor...")
    finally:
        if conexion.is_connected():
            conexion.disconnect()


if __name__ == "__main__":
    main()
