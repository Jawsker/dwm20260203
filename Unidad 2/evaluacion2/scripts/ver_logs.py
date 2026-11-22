#!/usr/bin/env python3
"""Muestra los registros JSON de los servicios en una línea legible por evento (para el video y la demostración).

  docker compose -f deploy/docker-compose.yml logs -f gateway auth orders inventory | python scripts/ver_logs.py
  docker compose -f deploy/docker-compose.yml logs -f gateway | python scripts/ver_logs.py --todo   (incluye las líneas "request")

Cada línea: hora · servicio · id de correlación · mensaje. El id de correlación es el MISMO en todos los
servicios que atendieron una misma solicitud del navegador: así se sigue un pedido de punta a punta.
"""
import json
import sys

COLOR = {"gateway": "\033[95m", "auth": "\033[96m", "orders": "\033[93m", "inventory": "\033[92m",
         "clients": "\033[94m", "payments": "\033[91m", "graphql": "\033[97m"}
FIN = "\033[0m"


def main():
    todo = "--todo" in sys.argv
    color = sys.stdout.isatty() or "--color" in sys.argv
    for linea in sys.stdin:
        i = linea.find("{")
        if i < 0:
            continue
        try:
            d = json.loads(linea[i:])
        except ValueError:
            continue
        if d.get("msg") == "request" and not todo:
            continue
        svc = d.get("service", "?")
        extra = f" [{d['method']} {d['route']} → {d['status']}, {d['ms']} ms]" if d.get("msg") == "request" else ""
        aviso = " ⚠" if d.get("level") in ("WARNING", "ERROR") else ""
        texto = f"{d.get('ts', '')[11:19]}  {svc:<9} cid={d.get('cid', '-')[:8]}  {d.get('msg')}{extra}{aviso}"
        print(f"{COLOR.get(svc, '')}{texto}{FIN}" if color else texto, flush=True)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
