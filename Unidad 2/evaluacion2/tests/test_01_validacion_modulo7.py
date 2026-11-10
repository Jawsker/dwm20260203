"""Los seis casos de validación exigidos en el Módulo 7, ejecutados contra el backend real.

Cada prueba indica: entrada, identidad, resultado esperado y componente que lo verifica.
"""
import httpx

from conftest import API, post_webhook, sign_event, place_order, stock_of


def test_V1_acceso_anonimo_al_catalogo(anon):
    """V1 · entrada: GET /products · identidad: anónimo · esperado: 200 con campos de catálogo, sin stock exacto.
    Verifica: API Gateway (ruta S01, auth=none) + Inventory (vista pública)."""
    r = anon.get("/products")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 12
    assert set(items[0]) == {"id", "categoria", "emoji", "nombre", "descripcion", "precio", "disponible"}
    assert "stock" not in items[0] and "reservado" not in items[0]


def test_V2_operacion_protegida_sin_sesion(anon):
    """V2 · entrada: POST /orders, GET /clients/me, POST /graphql · identidad: sin cookie · esperado: 401.
    Verifica: API Gateway (introspección contra Auth)."""
    for method, path, kw in [("POST", "/orders", {"json": {"items": [{"product_id": "p01", "qty": 1}]}}),
                             ("GET", "/clients/me", {}), ("POST", "/graphql", {"json": {"query": "{ yo { id } }"}}),
                             ("GET", "/admin/products", {})]:
        r = anon.req(method, path, **kw)
        assert r.status_code == 401, (path, r.text)
        assert r.json()["error"]["code"] == "unauthenticated"


def test_V2b_cookie_invalida_es_401(stack):
    from conftest import Api
    api = Api(stack.base)
    api.c.cookies.set("lr_session", "x" * 43)
    assert api.get("/auth/session").status_code == 401


def test_V3_administracion_con_rol_sin_permiso(ana, staff, audit):
    """V3 · entrada: operaciones de administración · identidad: customer/staff/auditor · esperado: 403.
    Verifica: API Gateway (roles por ruta) y, de forma independiente, el servicio dueño (defensa en profundidad)."""
    body = {"id": "pan-nuevo", "categoria": "panes", "nombre": "Pan nuevo", "descripcion": "Prueba de permisos", "precio": 1000, "stock": 5}
    assert ana.post("/admin/products", json=body).status_code == 403
    assert staff.post("/admin/products", json=body).status_code == 403          # staff no crea productos
    assert audit.post("/admin/products", json=body).status_code == 403
    assert ana.put("/admin/products/p01/stock", json={"stock": 999}).status_code == 403
    assert audit.put("/admin/products/p01/stock", json={"stock": 999}).status_code == 403  # auditoría solo supervisa
    assert ana.post("/admin/users", json={"email": "x@y.cl", "password": "una-clave-larga-1", "role": "admin"}).status_code == 403
    assert ana.post("/admin/maintenance/sweep").status_code == 403
    assert ana.get("/admin/contact").status_code == 403


def test_V4_pedido_ajeno_no_devuelve_datos(ana, beto, staff):
    """V4 · entrada: GET /orders/{id} y resumenPedido(id) · identidad: Beto sobre pedido de Ana · esperado: 404 sin datos;
    Ana y el personal sí lo ven. Verifica: Orders (regla de propiedad), aplicada en REST y detrás de GraphQL."""
    r = place_order(ana, [{"product_id": "p03", "qty": 1}], notes="sin nueces")
    assert r.status_code == 201, r.text
    oid = r.json()["id"]
    assert ana.get(f"/orders/{oid}").status_code == 200
    ajeno = beto.get(f"/orders/{oid}")
    assert ajeno.status_code == 404 and "p03" not in ajeno.text and "sin nueces" not in ajeno.text
    q = "query($id: ID!){ resumenPedido(id:$id){ id total notas } }"
    ok = ana.gql(q, {"id": oid}).json()
    assert ok["data"]["resumenPedido"]["id"] == oid
    nope = beto.gql(q, {"id": oid}).json()
    assert nope["data"] is None and nope["errors"][0]["extensions"]["code"] == "not_found"
    assert "sin nueces" not in str(nope)
    assert staff.get(f"/orders/{oid}").status_code == 200
    # ni el cliente ajeno puede pagar ni cancelar el pedido de otro
    assert beto.post(f"/orders/{oid}/pay").status_code == 404
    assert beto.post(f"/orders/{oid}/cancel").status_code == 404


def test_V5_acceso_directo_al_backend_sin_identidad(stack, ana):
    """V5 · entrada: llamadas directas a los puertos de servicios privados · identidad: ninguna / clave falsa / cabeceras
    de identidad inventadas · esperado: 401. Verifica: cada servicio (clave de arista por llamador, comparación en tiempo constante)."""
    for port, path in [(8003, "/internal/products"), (8004, "/internal/orders"), (8002, "/internal/clients/me"),
                       (8001, "/internal/login"), (8005, "/internal/payments"), (8006, "/graphql")]:
        r = httpx.request("POST" if path in ("/internal/login", "/internal/payments", "/graphql") else "GET",
                          f"http://127.0.0.1:{port}{path}", json={}, timeout=5)
        assert r.status_code == 401, (port, path, r.status_code)
        assert r.json()["error"]["code"] == "edge_unauthorized"
    forged = {"X-Edge-Caller": "gateway", "X-Edge-Key": "clave-inventada", "X-Auth-User": "u_admin", "X-Auth-Role": "admin"}
    assert httpx.get("http://127.0.0.1:8004/internal/orders", headers=forged, timeout=5).status_code == 401
    assert httpx.get("http://127.0.0.1:8003/internal/products", headers={"X-Edge-Caller": "nadie", "X-Edge-Key": "x"}, timeout=5).status_code == 401
    # Cabeceras de identidad enviadas por el navegador al gateway se descartan: sigue siendo Ana.
    r = ana.get("/auth/session", headers={"X-Auth-User": "u_admin", "X-Auth-Role": "admin", "X-Edge-Caller": "gateway"})
    assert r.json()["user_id"] == "u_ana" and r.json()["role"] == "customer"
    assert ana.post("/admin/maintenance/sweep", headers={"X-Auth-Role": "admin"}).status_code == 403
    # Los endpoints internos no se publican por el gateway
    assert ana.get("/../internal/products").status_code in (404, 400)
    assert httpx.get(f"{stack.base}/internal/products", timeout=5).status_code == 404


def test_V6_confirmar_pago_con_datos_alterados(stack, ana, beto, staff):
    """V6 · entrada: precio/total/estado alterados en la solicitud, endpoints de 'confirmación' inventados, webhooks falsificados,
    firma válida con monto distinto, repetición · esperado: el pedido solo pasa a pagado por el webhook firmado y verificado.
    Verifica: Orders (precio y total en servidor), Gateway (rutas), Payments (firma, monto, idempotencia)."""
    # 1) campos manipulados al crear el pedido: se ignoran
    r = ana.post("/orders", json={"items": [{"product_id": "p04", "qty": 2, "price": 1, "unit_price": 1}],
                                  "total": 1, "status": "paid", "payment": {"status": "succeeded"}})
    assert r.status_code == 201, r.text
    order = r.json()
    p = next(x for x in ana.get("/products").json()["items"] if x["id"] == "p04")
    assert order["total"] == p["precio"] * 2 and order["status"] == "awaiting_payment" and order["payment"]["status"] == "none"
    oid = order["id"]
    # 2) no existe forma de "confirmar" desde el navegador
    for method, path in [("POST", f"/orders/{oid}/confirm"), ("PUT", f"/orders/{oid}"), ("PATCH", f"/orders/{oid}"),
                         ("POST", f"/orders/{oid}/paid")]:
        assert ana.req(method, path, json={"status": "paid"}).status_code in (404, 405)
    assert ana.post(f"/admin/orders/{oid}/status", json={"status": "preparing"}).status_code == 403
    assert staff.post(f"/admin/orders/{oid}/status", json={"status": "preparing"}).status_code == 409  # no está pagado
    # 3) webhook sin firma, con firma mala y con firma vieja
    pay = ana.post(f"/orders/{oid}/pay").json()
    ref = pay["provider_ref"]
    evt = {"event_id": "evt_forjado_01", "type": "payment.succeeded", "provider_ref": ref, "amount": order["total"]}
    raw = __import__("json").dumps(evt, separators=(",", ":")).encode()
    assert post_webhook(stack, raw, None).status_code == 401
    assert post_webhook(stack, raw, "t=1,v1=00").status_code == 401
    raw2, sig2 = sign_event("secreto-equivocado", evt)
    assert post_webhook(stack, raw2, sig2).status_code == 401
    raw3, sig3 = sign_event(stack.webhook_secret, evt, ts=1_600_000_000)
    assert post_webhook(stack, raw3, sig3).status_code == 401  # firma correcta pero antigua (repetición)
    assert ana.get(f"/orders/{oid}").json()["status"] == "awaiting_payment"
    # 4) firma válida pero monto alterado: se rechaza y el pedido no cambia
    bad = dict(evt, event_id="evt_monto_01", amount=1)
    rawb, sigb = sign_event(stack.webhook_secret, bad)
    assert post_webhook(stack, rawb, sigb).status_code == 400
    assert ana.get(f"/orders/{oid}").json()["status"] == "awaiting_payment"
    # 5) otro usuario no puede 'decidir' el pago de Ana
    assert beto.post(f"/payments/{ref}/sandbox-decision", json={"outcome": "approve"}).status_code == 404
    # 6) camino legítimo: el proveedor (sandbox) notifica con firma válida
    before = stock_of(staff, "p04")
    d = ana.post(f"/payments/{ref}/sandbox-decision", json={"outcome": "approve"})
    assert d.status_code == 200 and d.json()["webhook_status"] == 200
    assert ana.get(f"/orders/{oid}").json()["status"] == "paid"
    after = stock_of(staff, "p04")
    assert after["stock"] == before["stock"] - 2 and after["reservado"] == before["reservado"] - 2
    # 7) repetir el mismo evento firmado no tiene efectos (idempotencia)
    ok = dict(evt, event_id="evt_legitimo_01")
    rawo, sigo = sign_event(stack.webhook_secret, ok)
    assert post_webhook(stack, rawo, sigo).status_code == 200
    assert post_webhook(stack, rawo, sigo).json().get("duplicate") is True
    assert stock_of(staff, "p04")["stock"] == after["stock"]
    # 8) un pago ya resuelto no se puede volver a decidir
    assert ana.post(f"/payments/{ref}/sandbox-decision", json={"outcome": "reject"}).status_code == 409
