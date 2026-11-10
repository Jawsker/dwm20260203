"""Flujos del caso y reglas críticas de negocio: registro/sesión, pedidos, stock, pagos, estados, expiración."""
import threading
import time
import uuid

import httpx

from conftest import Api, API, pay_and_decide, place_order, post_webhook, sign_event, stock_of, wait_for


# ---------------------------------------------------------------- registro, sesión y cuenta
def test_registro_login_logout_y_cookie_segura(stack):
    email = f"nuevo-{uuid.uuid4().hex[:6]}@ejemplo.cl"
    a = Api(stack.base)
    r = a.post("/auth/register", json={"email": email, "password": "Una-clave-larga-1", "nombre": "Persona Nueva",
                                       "telefono": "+56 9 5555 6666", "role": "admin"})
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role"] == "customer"                 # el rol no lo decide el cliente
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    token = a.c.cookies.get("lr_session")
    assert token and token not in r.text                          # el token no viaja en el cuerpo (JS no lo ve)
    assert a.get("/clients/me").json()["nombre"] == "Persona Nueva"
    assert a.post("/auth/register", json={"email": email, "password": "Una-clave-larga-1", "nombre": "Dup"}).status_code == 409
    assert Api(stack.base).post("/auth/register", json={"email": "otro@ejemplo.cl", "password": "corta", "nombre": "X"}).status_code == 400
    assert a.post("/auth/logout").status_code == 204
    revoked = Api(stack.base); revoked.c.cookies.set("lr_session", token)
    assert revoked.get("/auth/session").status_code == 401        # la sesión quedó revocada en Auth


def test_login_generico_y_bloqueo_por_intentos(stack):
    email = f"bloqueo-{uuid.uuid4().hex[:6]}@ejemplo.cl"
    Api(stack.base).post("/auth/register", json={"email": email, "password": "Una-clave-larga-1", "nombre": "Bloqueo"})
    a = Api(stack.base)
    r = a.post("/auth/login", json={"email": email, "password": "equivocada-123"})
    ghost = a.post("/auth/login", json={"email": "no-existe@ejemplo.cl", "password": "equivocada-123"})
    assert r.status_code == ghost.status_code == 401
    assert r.json()["error"]["message"] == ghost.json()["error"]["message"]   # no revela si el correo existe
    for _ in range(4):
        a.post("/auth/login", json={"email": email, "password": "equivocada-123"})
    assert a.post("/auth/login", json={"email": email, "password": "Una-clave-larga-1"}).status_code == 429  # bloqueada
    time.sleep(5.5)  # LR_LOGIN_LOCK_SECONDS=5 en el entorno de pruebas
    assert a.post("/auth/login", json={"email": email, "password": "Una-clave-larga-1"}).status_code == 200


def test_csrf_origen_y_tipo_de_contenido(stack, ana):
    evil = Api(stack.base, origin="http://evil.example")
    evil.c.cookies.set("lr_session", ana.c.cookies.get("lr_session"))
    assert evil.post("/orders", json={"items": [{"product_id": "p01", "qty": 1}]}).status_code == 403
    sin_origen = Api(stack.base, origin=None)
    sin_origen.c.cookies.set("lr_session", ana.c.cookies.get("lr_session"))
    assert sin_origen.post("/orders", json={"items": [{"product_id": "p01", "qty": 1}]}).status_code == 403
    assert ana.post("/orders", content="items=1", headers={"Content-Type": "text/plain"}).status_code == 415
    assert ana.post("/orders", content=b"x" * 5000, headers={"Content-Type": "application/json"}).status_code == 413


def test_rutas_inexistentes_y_verbos_no_permitidos(anon):
    assert anon.get("/internal/products").status_code == 404
    assert anon.req("DELETE", "/products").status_code == 405
    assert anon.get("/products", params={"categoria": "inexistente"}).status_code == 400
    assert anon.get("/products", params={"limit": 1000}).status_code == 400
    assert anon.get("/products", params={"categoria": "panes"}).json()["total"] >= 1
    r = anon.get("/nada")
    assert r.status_code == 404 and r.json()["error"]["correlation_id"] and r.headers["x-correlation-id"]


def test_formulario_de_contacto_y_limite_de_solicitudes(stack, staff, ana):
    a = Api(stack.base)
    body = {"nombre": "Visita", "correo": "visita@ejemplo.cl", "mensaje": "Hola, ¿tienen pan de molde?"}
    assert a.post("/contact", json=body).status_code == 201
    assert any(m["correo"] == "visita@ejemplo.cl" for m in staff.get("/admin/contact").json()["items"])
    assert ana.get("/admin/contact").status_code == 403
    codes = [a.post("/contact", json=body).status_code for _ in range(6)]
    assert 429 in codes                                            # clase "contact": 5 por minuto e IP


# ---------------------------------------------------------------- pedidos, stock y pagos
def test_flujo_completo_pedido_pago_y_preparacion(ana, staff):
    inicial = stock_of(staff, "p02")
    r = place_order(ana, [{"product_id": "p02", "qty": 3}])
    oid = r.json()["id"]
    reservado = stock_of(staff, "p02")
    assert reservado["disponible_unidades"] == inicial["disponible_unidades"] - 3 and reservado["stock"] == inicial["stock"]
    pay_and_decide(ana, oid, "approve")
    final = stock_of(staff, "p02")
    assert final["stock"] == inicial["stock"] - 3 and final["reservado"] == inicial["reservado"]
    assert ana.get(f"/orders/{oid}").json()["status"] == "paid"
    assert ana.post(f"/admin/orders/{oid}/status", json={"status": "preparing"}).status_code == 403   # cliente no cambia estados
    assert staff.post(f"/admin/orders/{oid}/status", json={"status": "ready"}).status_code == 409     # no se salta pasos
    for s in ("preparing", "ready", "delivered"):
        assert staff.post(f"/admin/orders/{oid}/status", json={"status": s}).json()["status"] == s
    assert staff.post(f"/admin/orders/{oid}/status", json={"status": "preparing"}).status_code == 409  # terminal
    assert ana.post(f"/orders/{oid}/cancel").status_code == 409                                         # pagado no se cancela


def test_pago_rechazado_conserva_pedido_y_permite_reintento(ana):
    oid = place_order(ana, [{"product_id": "p05", "qty": 1}]).json()["id"]
    pay_and_decide(ana, oid, "reject")
    o = ana.get(f"/orders/{oid}").json()
    assert o["status"] == "awaiting_payment" and o["payment"]["status"] == "failed"
    pay_and_decide(ana, oid, "approve")
    assert ana.get(f"/orders/{oid}").json()["status"] == "paid"
    assert ana.post(f"/orders/{oid}/pay").status_code == 409        # no se paga dos veces


def test_cancelar_libera_el_stock(ana, staff):
    antes = stock_of(staff, "p06")
    oid = place_order(ana, [{"product_id": "p06", "qty": 4}]).json()["id"]
    assert stock_of(staff, "p06")["disponible_unidades"] == antes["disponible_unidades"] - 4
    assert ana.post(f"/orders/{oid}/cancel").json()["status"] == "cancelled"
    assert stock_of(staff, "p06")["disponible_unidades"] == antes["disponible_unidades"]
    assert ana.post(f"/orders/{oid}/cancel").status_code == 409


def test_stock_insuficiente_y_validaciones_del_pedido(ana):
    r = place_order(ana, [{"product_id": "p07", "qty": 20}])
    assert r.status_code == 201
    r = place_order(ana, [{"product_id": "p07", "qty": 5}])
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_stock"
    assert r.json()["error"]["details"][0]["disponible"] == 0
    assert place_order(ana, [{"product_id": "no-existe", "qty": 1}]).status_code == 409
    assert place_order(ana, []).status_code == 400
    assert place_order(ana, [{"product_id": "p01", "qty": 0}]).status_code == 400
    assert place_order(ana, [{"product_id": "p01", "qty": 21}]).status_code == 400
    assert place_order(ana, [{"product_id": "p01", "qty": 1}, {"product_id": "p01", "qty": 1}]).status_code == 400


def test_concurrencia_no_se_vende_mas_de_lo_que_hay(ana, beto, staff):
    assert staff.put("/admin/products/p12/stock", json={"stock": 3}).status_code == 200
    results = []

    def buy(api):
        results.append(place_order(api, [{"product_id": "p12", "qty": 1}]).status_code)

    threads = [threading.Thread(target=buy, args=(ana if i % 2 else beto,)) for i in range(10)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results).count(201) == 3 and results.count(409) == 7, results
    s = stock_of(staff, "p12")
    assert s["disponible_unidades"] == 0 and s["reservado"] == 3


def test_idempotency_key_no_duplica_pedidos(ana, staff):
    antes = stock_of(staff, "p08")["disponible_unidades"]
    key = uuid.uuid4().hex
    a = place_order(ana, [{"product_id": "p08", "qty": 2}], key=key)
    b = place_order(ana, [{"product_id": "p08", "qty": 2}], key=key)
    assert a.status_code == 201 and b.json()["id"] == a.json()["id"] and b.json().get("replayed") is True
    assert stock_of(staff, "p08")["disponible_unidades"] == antes - 2


def test_expiracion_libera_stock_y_pago_tardio_requiere_reembolso(stack, ana, staff):
    antes = stock_of(staff, "p10")["disponible_unidades"]
    oid = place_order(ana, [{"product_id": "p10", "qty": 2}]).json()["id"]
    ref = ana.post(f"/orders/{oid}/pay").json()["provider_ref"]
    expirado = wait_for(lambda: ana.get(f"/orders/{oid}").json()["status"] == "expired", timeout=14)
    assert expirado, "el pedido debía expirar (TTL=6 s en pruebas)"
    assert stock_of(staff, "p10")["disponible_unidades"] == antes                 # stock recuperado
    assert ana.post(f"/orders/{oid}/pay").status_code == 409
    # el proveedor igual cobra tarde: el sistema no pierde el dinero ni reactiva el pedido
    ana.post(f"/payments/{ref}/sandbox-decision", json={"outcome": "approve"})
    o = ana.get(f"/orders/{oid}").json()
    assert o["status"] == "refund_required" and o["refund_required"] is True
    assert stock_of(staff, "p10")["disponible_unidades"] == antes


def test_panel_de_administracion_y_productos(admin, staff, ana):
    p = {"id": "pan-prueba", "categoria": "panes", "emoji": "🥐", "nombre": "Pan de prueba",
         "descripcion": "Producto creado por la prueba", "precio": 1500, "stock": 4}
    assert admin.post("/admin/products", json=p).status_code == 201
    assert admin.post("/admin/products", json=p).status_code == 409
    assert admin.put("/admin/products/pan-prueba", json={"precio": 1700}).json()["precio"] == 1700
    assert admin.put("/admin/products/pan-prueba", json={"precio": -5}).status_code == 400
    assert staff.put("/admin/products/pan-prueba/stock", json={"stock": 9}).json()["disponible_unidades"] == 9
    low = staff.get("/admin/products").json()["items"]
    assert all("stock" in x for x in low)
    nuevo = admin.post("/admin/users", json={"email": f"s-{uuid.uuid4().hex[:5]}@libreyrico.test",
                                             "password": "Clave-del-personal-1", "role": "staff"})
    assert nuevo.status_code == 201


def test_eliminar_cuenta_borra_perfil_y_anonimiza_pedidos(stack, staff):
    email = f"baja-{uuid.uuid4().hex[:6]}@ejemplo.cl"
    u = Api(stack.base)
    u.post("/auth/register", json={"email": email, "password": "Una-clave-larga-1", "nombre": "Para Baja"})
    oid = place_order(u, [{"product_id": "p09", "qty": 1}], notes="mi nota").json()["id"]
    assert u.delete("/account").status_code == 204
    assert Api(stack.base).post("/auth/login", json={"email": email, "password": "Una-clave-larga-1"}).status_code == 401
    o = staff.get(f"/orders/{oid}").json()
    assert o["customer_id"].startswith("deleted-") and o["notes"] is None


def test_los_logs_no_contienen_credenciales_ni_datos_personales(stack):
    blob = ""
    for f in (stack.log_dir).glob("*.log"):
        blob += f.read_text(errors="ignore")
    assert blob  # hay logs
    assert stack.seed_password not in blob and stack.webhook_secret not in blob
    assert "lr_session" not in blob and "@ejemplo.cl" not in blob and "+56 9" not in blob
    assert all(k not in blob for k in stack.edge_keys.values())


def test_filtros_del_catalogo_texto_y_disponibilidad(anon, admin):
    """RF2 · entrada: GET /products con q, categoria y available · identidad: anónimo · esperado: solo coincidencias; agotados se excluyen con available=true."""
    todos = anon.get("/products", params={"limit": 100}).json()
    assert todos["total"] >= 12
    nombre = todos["items"][0]["nombre"]
    por_texto = anon.get("/products", params={"q": nombre[:6]}).json()
    assert por_texto["total"] >= 1 and all(nombre[:6].lower() in (i["nombre"] + i["descripcion"]).lower() for i in por_texto["items"])
    assert anon.get("/products", params={"q": "zzzz-no-existe"}).json()["total"] == 0
    p = {"id": "pan-agotado", "categoria": "panes", "nombre": "Pan agotado", "descripcion": "Sin stock para el filtro", "precio": 900, "stock": 0}
    assert admin.post("/admin/products", json=p).status_code == 201
    ids_disp = {i["id"] for i in anon.get("/products", params={"available": "true", "limit": 100}).json()["items"]}
    ids_todos = {i["id"] for i in anon.get("/products", params={"limit": 100}).json()["items"]}
    assert "pan-agotado" in ids_todos and "pan-agotado" not in ids_disp


def test_stock_fisico_no_baja_de_lo_reservado(ana, admin, staff):
    """RN10 · entrada: ajuste de stock menor que lo reservado · identidad: personal · esperado: 409 stock_below_reserved; igual a lo reservado, 200."""
    p = {"id": "pan-reserva", "categoria": "panes", "nombre": "Pan reserva", "descripcion": "Para probar la regla", "precio": 1000, "stock": 5}
    assert admin.post("/admin/products", json=p).status_code == 201
    o = place_order(ana, [{"product_id": "pan-reserva", "qty": 3}])
    assert o.status_code == 201, o.text
    r = staff.put("/admin/products/pan-reserva/stock", json={"stock": 2})
    assert r.status_code == 409 and r.json()["error"]["code"] == "stock_below_reserved"
    assert staff.put("/admin/products/pan-reserva/stock", json={"stock": 3}).status_code == 200
    ana.post(f"/orders/{o.json()['id']}/cancel")
