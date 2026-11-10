"""GraphQL Gateway: agregación real de varios subsistemas, autorización por campo y límites de consulta."""
from conftest import place_order

PEDIDOS = """
query($n:Int){ pedidos(primeros:$n){ total items{ id estado total lineas{ nombre cantidad subtotal producto{ emoji precio disponible } }
  cliente{ id nombre telefono } } } }
"""


def test_agregacion_pedidos_con_productos_vigentes(ana):
    oid = place_order(ana, [{"product_id": "p01", "qty": 2}, {"product_id": "p11", "qty": 1}]).json()["id"]
    r = ana.gql("query($id:ID!){ resumenPedido(id:$id){ id estado total lineas{ nombre cantidad subtotal producto{ id emoji precio disponible } } } }",
                {"id": oid}).json()
    assert "errors" not in r, r
    p = r["data"]["resumenPedido"]
    assert p["estado"] == "awaiting_payment" and len(p["lineas"]) == 2
    # los datos de producto vienen de inventory (emoji/disponible) y los montos de orders: dos subsistemas en una consulta
    assert all(l["producto"]["emoji"] and l["producto"]["disponible"] is True for l in p["lineas"])
    assert p["total"] == sum(l["subtotal"] for l in p["lineas"])


def test_cliente_ve_solo_lo_suyo_y_no_el_campo_cliente(ana, beto):
    place_order(ana, [{"product_id": "p01", "qty": 1}])
    r = ana.gql(PEDIDOS, {"n": 50}).json()
    assert r["data"]["pedidos"]["items"], "Ana debe ver sus pedidos"
    ids_ana = {p["id"] for p in r["data"]["pedidos"]["items"]}
    ids_beto = {p["id"] for p in (beto.gql(PEDIDOS, {"n": 50}).json()["data"]["pedidos"]["items"])}
    assert ids_ana.isdisjoint(ids_beto)
    # campo restringido: error parcial, el resto de la respuesta se entrega y el teléfono no sale
    assert r["errors"] and r["errors"][0]["extensions"]["code"] == "forbidden"
    assert all(p["cliente"] is None for p in r["data"]["pedidos"]["items"]) and "+56" not in str(r["data"])


def test_personal_ve_clientes_y_auditoria_no(ana, staff, audit):
    place_order(ana, [{"product_id": "p01", "qty": 1}], notes="nota privada")
    s = staff.gql(PEDIDOS, {"n": 50}).json()
    assert "errors" not in s, s
    nombres = {p["cliente"]["nombre"] for p in s["data"]["pedidos"]["items"] if p["cliente"]}
    assert any("Ana" in n for n in nombres)
    a = audit.gql("{ pedidos(primeros:5){ total items{ id estado notas clienteRef cliente{ nombre } } } }").json()
    assert a["data"]["pedidos"]["total"] > 0
    first = a["data"]["pedidos"]["items"][0]
    assert first["notas"] is None and first["clienteRef"] and first["cliente"] is None   # sin identidad ni notas
    assert a["errors"][0]["extensions"]["code"] == "forbidden"
    assert "nota privada" not in str(a) and "Ana" not in str(a)


def test_panel_operacion_agrega_orders_e_inventory(staff, audit, ana):
    q = "{ panelOperacion{ ventasPagadas pedidosPorEstado{ estado cantidad } productosBajoStock{ id unidadesDisponibles } } }"
    s = staff.gql(q).json()
    assert "errors" not in s and s["data"]["panelOperacion"]["pedidosPorEstado"]
    assert any(p["id"] == "p12" for p in s["data"]["panelOperacion"]["productosBajoStock"])   # p12 quedó sin stock en otra prueba
    a = audit.gql(q).json()
    assert a["data"]["panelOperacion"]["pedidosPorEstado"] and a["data"]["panelOperacion"]["productosBajoStock"] is None
    assert a["errors"][0]["extensions"]["code"] == "forbidden"                     # auditoría no ve stock
    assert ana.gql(q).json()["errors"][0]["extensions"]["code"] == "forbidden"


def _errors(r):
    return " | ".join(e["message"] for e in r.json().get("errors", []))


def test_limites_de_consulta(ana):
    assert "5 aliases" in _errors(ana.gql("{ yo{ id } a: yo{ id } b: yo{ id } c: yo{ id } d: yo{ id } e: yo{ id } }"))
    big = "{ pedidos{ items{ id " + "id " * 700 + "} } }"
    assert "tokens" in _errors(ana.gql(big))
    assert "introspection" in _errors(ana.gql("{ __schema{ types{ name } } }"))
    r = ana.gql("{ pedidos(primeros: 500){ total } }").json()
    assert r["errors"][0]["extensions"]["code"] == "validation_error"          # paginación acotada
    assert "Traceback" not in str(ana.gql("{ campoInexistente }").json())
    assert ana.get("/graphql").status_code == 405                              # solo POST
