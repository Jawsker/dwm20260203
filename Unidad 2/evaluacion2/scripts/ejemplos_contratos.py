#!/usr/bin/env python3
"""Ejecuta las 26 operaciones externas contra el stack local y guarda una solicitud/respuesta REAL de cada una
(Módulo 1: «ejemplo JSON con datos ficticios»). Se redactan cookies y secretos."""
import hashlib, hmac, json, sys, time, uuid
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dev_local import Stack  # noqa: E402

OUT = ROOT / "docs" / "evidencia" / "ejemplos-contratos.md"
O = {"Origin": "http://localhost:8080"}
P = "/api/v1"
LOG = {}


def main():
    st = Stack(overrides={"LR_RATE_LOGIN": "500", "LR_RATE_WRITE": "500"}).start()
    try:
        def client(): return httpx.Client(base_url=st.base, headers=O, timeout=15)
        def call(sid, c, method, path, body=None, headers=None, note=""):
            r = c.request(method, P + path, json=body, headers=headers or {})
            try: data = r.json()
            except Exception: data = None
            LOG[sid] = LOG.get(sid, []) + [(note, method, path, body, headers, r.status_code, data)]
            return r, data
        def login(email):
            c = client(); c.post(P + "/auth/login", json={"email": email, "password": st.seed_password}); return c

        anon = client(); ana = login("ana@ejemplo.cl"); staff = login("tienda@libreyrico.test"); admin = login("admin@libreyrico.test")
        call("S01", anon, "GET", "/products?available=true&limit=2")
        call("S01", anon, "GET", "/products?categoria=inexistente", note="filtro inválido")
        call("S02", anon, "GET", "/products/p01")
        nuevo = client(); email = f"cliente-{uuid.uuid4().hex[:4]}@ejemplo.cl"
        call("S03", nuevo, "POST", "/auth/register", {"email": email, "password": "Clave-ficticia-123", "nombre": "Cliente Ficticio", "telefono": "+56 9 1234 5678"})
        call("S04", anon, "POST", "/auth/login", {"email": "ana@ejemplo.cl", "password": "incorrecta-123"}, note="credenciales inválidas")
        call("S06", nuevo, "GET", "/auth/session")
        call("S07", nuevo, "GET", "/clients/me")
        call("S08", nuevo, "PUT", "/clients/me", {"direccion": "Calle Ficticia 123, Santiago"})
        call("S10", anon, "POST", "/contact", {"nombre": "Visitante Ficticio", "correo": "visita@ejemplo.cl", "mensaje": "¿Tienen pan sin gluten por encargo?"})
        call("S11", staff, "GET", "/admin/contact?limit=2")
        r, o = call("S12", ana, "POST", "/orders", {"items": [{"product_id": "p01", "qty": 2}, {"product_id": "p03", "qty": 1}], "notes": "retiro en la tarde"}, {"Idempotency-Key": "demo-0001"})
        oid = o["id"]
        call("S13", ana, "GET", f"/orders/{oid}")
        call("S13", client() if False else login("beto@ejemplo.cl"), "GET", f"/orders/{oid}", note="otro cliente → no ve datos")
        r, pay = call("S14", ana, "POST", f"/orders/{oid}/pay")
        ref = pay["provider_ref"]
        call("S17", ana, "GET", f"/payments/{ref}")
        call("S18", ana, "POST", f"/payments/{ref}/sandbox-decision", {"outcome": "approve"})
        ev = {"event_id": "evt_demo_" + uuid.uuid4().hex[:6], "type": "payment.succeeded", "provider_ref": ref, "amount": o["total"]}
        raw = json.dumps(ev, separators=(",", ":")).encode(); ts = int(time.time())
        mac = hmac.new(st.webhook_secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        r = httpx.post(st.base + P + "/webhooks/payments", content=raw, headers={"Content-Type": "application/json", "X-Provider-Signature": f"t={ts},v1=<hmac redactado>"}, timeout=10)
        r2 = httpx.post(st.base + P + "/webhooks/payments", content=raw, headers={"Content-Type": "application/json", "X-Provider-Signature": f"t={ts},v1={mac}"}, timeout=10)
        r3 = httpx.post(st.base + P + "/webhooks/payments", content=raw, headers={"Content-Type": "application/json", "X-Provider-Signature": f"t={ts},v1=firma-falsa"}, timeout=10)
        LOG["S19"] = [("evento ya procesado por la decisión sandbox, firma válida", "POST", "/webhooks/payments", ev, {"X-Provider-Signature": "t=<epoch>,v1=<hmac-sha256 redactado>"}, r2.status_code, r2.json()),
                      ("firma falsa", "POST", "/webhooks/payments", ev, {"X-Provider-Signature": "t=<epoch>,v1=firma-falsa"}, r3.status_code, r3.json())]
        call("S16", staff, "POST", f"/admin/orders/{oid}/status", {"status": "preparing"})
        call("S20", ana, "POST", "/graphql", {"query": "query { pedidos(primeros: 1) { total items { id estado total lineas { nombre cantidad } } } }"})
        call("S21", staff, "GET", "/admin/products?limit=2")
        call("S22", admin, "POST", "/admin/products", {"id": "pan-demo", "categoria": "panes", "emoji": "🍞", "nombre": "Pan demo", "descripcion": "Producto ficticio de ejemplo", "precio": 2500, "stock": 10})
        call("S23", admin, "PUT", "/admin/products/pan-demo", {"precio": 2700})
        call("S24", staff, "PUT", "/admin/products/pan-demo/stock", {"stock": 8})
        call("S25", admin, "POST", "/admin/users", {"email": f"personal-{uuid.uuid4().hex[:4]}@libreyrico.test", "password": "Clave-ficticia-123", "role": "staff"})
        call("S26", admin, "POST", "/admin/maintenance/sweep")
        r, o2 = call("S12", ana, "POST", "/orders", {"items": [{"product_id": "p02", "qty": 1}]}, note="segundo pedido, para cancelar")
        call("S15", ana, "POST", f"/orders/{o2['id']}/cancel")
        call("S05", nuevo, "POST", "/auth/logout")
        baja = client(); baja.post(P + "/auth/register", json={"email": f"baja-{uuid.uuid4().hex[:4]}@ejemplo.cl", "password": "Clave-ficticia-123", "nombre": "Para Baja"})
        call("S09", baja, "DELETE", "/account")

        out = ["# Ejemplos reales de contratos S01–S26 (Módulo 1)\n",
               "Generado por `python scripts/ejemplos_contratos.py` ejecutando cada operación contra el stack local con **datos ficticios**. Ids, fechas y referencias son de esa ejecución; cookies y firmas se redactan.\n"]
        for sid in sorted(LOG):
            for note, m, path, body, hd, code, data in LOG[sid]:
                out.append(f"## {sid} · `{m} {P}{path}`" + (f" — {note}" if note else "") + "\n")
                if hd: out.append("Cabeceras relevantes: `" + json.dumps(hd, ensure_ascii=False) + "`\n")
                if body is not None: out += ["Solicitud:", "```json", json.dumps(body, indent=2, ensure_ascii=False), "```"]
                out += [f"Respuesta **{code}**:", "```json", json.dumps(data, indent=2, ensure_ascii=False)[:1800], "```\n"]
        OUT.write_text("\n".join(out), encoding="utf-8")
        print("ok", len(LOG), "operaciones;", sum(len(v) for v in LOG.values()), "ejemplos")
        print({k: [x[5] for x in v] for k, v in sorted(LOG.items())})
    finally:
        st.stop()


main()
