#!/usr/bin/env python3
"""Productor STOMP de prueba: publica un evento de pedido en /queue/pedidos (JSON o XML).

En el sistema real quien publica es el servicio Orders al confirmarse un pago (ver
apigateway/common/lr_common/mensajeria.py). Este script sirve para probar el broker y el consumidor a mano.

  export STOMP_USUARIO=...  STOMP_CLAVE=...        (las credenciales NO van en el código ni en la línea de comandos)
  python productor.py --formato json --id LR-DEMO01 --total 9370 --lineas 2
  python productor.py --formato xml  --id LR-DEMO01 --total 9370 --lineas 2
"""
import argparse
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import stomp

DESTINO = "/queue/pedidos"


def construir_mensaje(formato: str, evento: dict) -> tuple[str, str]:
    if formato == "json":
        return json.dumps(evento, ensure_ascii=False), "application/json; charset=utf-8"
    if formato == "xml":
        raiz = ET.Element("pedido")
        for clave, valor in evento.items():
            ET.SubElement(raiz, clave).text = str(valor)
        return ET.tostring(raiz, encoding="unicode"), "application/xml; charset=utf-8"
    raise ValueError(f"Formato desconocido: {formato}")


def main():
    parser = argparse.ArgumentParser(description="Productor STOMP de eventos de pedido (Libre & Rico)")
    parser.add_argument("--formato", choices=["json", "xml"], default="json")
    parser.add_argument("--id", default="LR-DEMO01")
    parser.add_argument("--total", type=int, default=9370)
    parser.add_argument("--lineas", type=int, default=2)
    parser.add_argument("--host", default=os.getenv("LR_STOMP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("LR_STOMP_PORT", "61613")))
    parser.add_argument("--vhost", default=os.getenv("LR_STOMP_VHOST", "/"))
    args = parser.parse_args()
    usuario, clave = os.getenv("STOMP_USUARIO"), os.getenv("STOMP_CLAVE")
    if not usuario or not clave:
        parser.error("Define STOMP_USUARIO y STOMP_CLAVE en el entorno.")
    if args.total < 0 or args.lineas < 1:
        parser.error("--total debe ser ≥ 0 y --lineas ≥ 1")

    evento = {"evento": "pedido_pagado", "id": args.id, "estado": "paid", "total": args.total, "lineas": args.lineas,
              "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    cuerpo, mime = construir_mensaje(args.formato, evento)
    conexion = stomp.Connection12([(args.host, args.port)], vhost=args.vhost)
    try:
        conexion.connect(usuario, clave, wait=True)
        conexion.send(destination=DESTINO, body=cuerpo,
                      headers={"content-type": mime, "x-formato": args.formato, "persistent": "true"})
        print(f"Mensaje enviado a {DESTINO} (formato={args.formato}):\n{cuerpo}")
    finally:
        if conexion.is_connected():
            conexion.disconnect()


if __name__ == "__main__":
    main()
