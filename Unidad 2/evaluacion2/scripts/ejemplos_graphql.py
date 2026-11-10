#!/usr/bin/env python3
"""Captura consultas/respuestas GraphQL REALES contra el stack local (evidencia del Módulo 8)."""
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dev_local import Stack  # noqa: E402

OUT = ROOT / "docs" / "evidencia" / "ejemplos-graphql.md"
O = {"Origin": "http://localhost:8080"}

Q_PEDIDOS = """query {
  pedidos(primeros: 2) {
    total
    items { id estado total lineas { nombre cantidad subtotal producto { precio disponible } } cliente { nombre } }
  }
}"""
Q_PANEL = "query { panelOperacion { pedidosPorEstado { estado cantidad } ventasPagadas productosBajoStock { nombre unidadesDisponibles } } }"
Q_AJENO = 'query { resumenPedido(id: "%s") { id total } }'


def main():
    st = Stack(overrides={"LR_RATE_LOGIN": "500", "LR_RATE_WRITE": "500"}).start()
    try:
        def sess(email):
            c = httpx.Client(base_url=st.base, headers=O, timeout=15)
            assert c.post("/api/v1/auth/login", json={"email": email, "password": st.seed_password}).status_code == 200
            return c
        gql = lambda c, q: c.post("/api/v1/graphql", json={"query": q}).json()
        ana, beto, staff, aud = sess("ana@ejemplo.cl"), sess("beto@ejemplo.cl"), sess("tienda@libreyrico.test"), sess("auditoria@libreyrico.test")
        r = ana.post("/api/v1/orders", json={"items": [{"product_id": "p01", "qty": 2}, {"product_id": "p03", "qty": 1}]}, headers={"Idempotency-Key": "ejemplo-1"})
        assert r.status_code == 201, r.text
        oid = r.json()["id"]
        casos = [
            ("1. Cliente (Ana) consulta sus pedidos: agrega orders + inventory; el campo `cliente` queda prohibido", ana, Q_PEDIDOS),
            ("2. Personal consulta los mismos pedidos: ahora sí ve `cliente` (clients), sin dirección", staff, Q_PEDIDOS),
            ("3. Otro cliente (Beto) pide el pedido de Ana por id", beto, Q_AJENO % oid),
            ("4. Auditoría pide el panel: pedidos y ventas sí; bajo stock → error parcial si el rol no lo permite", aud, Q_PANEL),
            ("5. Personal pide el panel completo (orders + inventory)", staff, Q_PANEL),
        ]
        out = ["# Ejemplos reales de GraphQL (Módulo 8)\n", "Generado por `python scripts/ejemplos_graphql.py` contra el stack local; los ids y montos son de esa ejecución.\n"]
        for t, c, q in casos:
            out += [f"## {t}\n", "```graphql", q, "```", "```json", json.dumps(gql(c, q), indent=2, ensure_ascii=False), "```\n"]
        OUT.write_text("\n".join(out), encoding="utf-8")
        print("escrito", OUT)
    finally:
        st.stop()


main()
