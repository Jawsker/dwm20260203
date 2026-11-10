"""Indisponibilidad de dependencias. Va al final: detiene y reinicia procesos del stack local."""
import httpx

from conftest import place_order


def test_inventory_caido_degrada_de_forma_controlada(stack, ana):
    oid = place_order(ana, [{"product_id": "p01", "qty": 1}]).json()["id"]
    stack.stop_service("inventory")
    try:
        r = httpx.get(f"{stack.base}/api/v1/products", timeout=15)
        assert r.status_code == 503 and r.json()["error"]["code"] == "upstream_unavailable"
        assert "Traceback" not in r.text and "127.0.0.1" not in r.text           # sin detalles internos
        # crear pedido necesita inventory: falla limpio y deja el pedido rechazado, no colgado
        n = place_order(ana, [{"product_id": "p01", "qty": 1}])
        assert n.status_code == 503
        # GraphQL: el pedido (orders) se entrega; el producto (inventory) llega null con error parcial
        q = ana.gql("query($id:ID!){ resumenPedido(id:$id){ id estado lineas{ nombre producto{ emoji } } } }", {"id": oid}).json()
        assert q["data"]["resumenPedido"]["id"] == oid and q["data"]["resumenPedido"]["lineas"][0]["producto"] is None
        assert q["errors"][0]["extensions"]["code"] == "upstream_unavailable"
    finally:
        stack.start_service("inventory")


def test_orders_caido_da_503_y_se_recupera(stack, ana):
    stack.stop_service("orders")
    try:
        r = ana.get("/orders/LR-00000000")
        assert r.status_code == 503 and r.json()["error"]["code"] == "upstream_unavailable"
        assert ana.get("/products").status_code == 200                              # el catálogo sigue vivo
    finally:
        stack.start_service("orders")
    assert ana.get("/orders/LR-00000000").status_code == 404


def test_auth_caido_falla_cerrado(stack, ana):
    stack.stop_service("auth")
    try:
        r = ana.get("/clients/me")
        assert r.status_code == 503                                                   # nunca "deja pasar" sin validar sesión
        assert ana.get("/products").status_code == 200                                # lo anónimo sigue funcionando
    finally:
        stack.start_service("auth")


def test_limite_de_profundidad_graphql(stack):
    """El esquema actual llega a profundidad 5; se reinicia graphql con límite 3 para probar el rechazo."""
    from conftest import Api
    # Auth se reinició en la prueba anterior (base en memoria): hay que abrir sesión de nuevo.
    ana = Api(stack.base).login("ana@ejemplo.cl", stack.seed_password)
    q5 = "{ pedidos(primeros:1){ items{ lineas{ producto{ emoji } } } } }"
    assert "errors" not in ana.gql(q5).json()                                      # límite de producción (6): pasa
    stack.stop_service("graphql")
    stack.start_service("graphql", env={"LR_GQL_MAX_DEPTH": "3"})
    try:
        r = ana.gql(q5).json()
        assert r["data"] is None and "depth" in r["errors"][0]["message"].lower()
        assert "errors" not in ana.gql("{ pedidos(primeros:1){ items{ id estado } } }").json()
    finally:
        stack.stop_service("graphql")
        stack.start_service("graphql")
