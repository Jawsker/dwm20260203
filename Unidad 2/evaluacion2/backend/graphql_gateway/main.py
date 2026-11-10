"""GraphQL Gateway (privado). Agregación de lectura para el frontend.

* Solo es alcanzable desde el API Gateway (clave de arista gateway→graphql); no tiene puerto público.
* NO accede a bases de datos: compone llamadas a las APIs internas de orders, inventory y clients.
* NO decide la autorización: reenvía la identidad verificada y cada servicio dueño del dato aplica
  su regla (propiedad del pedido, campos por rol). Un campo que el rol no puede ver sale como error
  parcial con ``extensions.code`` y valor null, sin filtrar el dato.
* Las reglas transaccionales (crear, pagar, cancelar, cambiar estado) siguen siendo REST en orders:
  este esquema no define mutations.
* Límites: profundidad, alias, tokens, introspección desactivada, paginación máxima y plazos por llamada.
"""
from __future__ import annotations

import os
from typing import Optional

import strawberry
from fastapi import Depends
from graphql import GraphQLError
from strawberry.dataloader import DataLoader
from strawberry.extensions import (DisableIntrospection, MaskErrors, MaxAliasesLimiter, MaxTokensLimiter,
                                   QueryDepthLimiter)
from strawberry.fastapi import GraphQLRouter

from lr_common.client import ServiceClient
from lr_common.web import ApiError, Edge, create_app, edge_guard

SERVICE = "graphql"
app = create_app(SERVICE)
guard = edge_guard(SERVICE, allowed=["gateway"], identity_from=["gateway"])

TIMEOUT = float(os.getenv("LR_GQL_DOWNSTREAM_TIMEOUT", "2.5"))
orders_api = ServiceClient(SERVICE, "orders", "LR_ORDERS_URL", "http://orders:8000", timeout=TIMEOUT)
inventory_api = ServiceClient(SERVICE, "inventory", "LR_INVENTORY_URL", "http://inventory:8000", timeout=TIMEOUT)
clients_api = ServiceClient(SERVICE, "clients", "LR_CLIENTS_URL", "http://clients:8000", timeout=TIMEOUT)


def fail(exc: ApiError) -> GraphQLError:
    return GraphQLError(exc.message, extensions={"code": exc.code, "status": exc.status})


# ------------------------------------------------------------------ tipos
@strawberry.type
class Producto:
    id: str
    nombre: str
    emoji: str
    descripcion: str
    precio: int
    disponible: bool


@strawberry.type
class Cliente:
    id: str
    nombre: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]


@strawberry.type
class LineaPedido:
    producto_id: str
    nombre: str
    cantidad: int
    precio_unitario: int
    subtotal: int

    @strawberry.field(description="Datos VIGENTES del producto (inventory). Null si inventory no responde.")
    async def producto(self, info: strawberry.Info) -> Optional[Producto]:
        try:
            return await info.context["loaders"]["productos"].load(self.producto_id)
        except ApiError as exc:
            raise fail(exc)


@strawberry.type
class Pedido:
    id: str
    estado: str
    total: int
    moneda: str
    creado: str
    expira: Optional[str]
    estado_pago: str
    requiere_reembolso: bool
    notas: Optional[str]
    cliente_ref: Optional[str]
    lineas: list[LineaPedido]
    _cliente_id: strawberry.Private[Optional[str]] = None

    @strawberry.field(description="Perfil del cliente. Solo personal de tienda y administración.")
    async def cliente(self, info: strawberry.Info) -> Optional[Cliente]:
        ident = info.context["identity"]
        if ident.role not in ("staff", "admin"):
            raise GraphQLError("Tu rol no puede consultar datos del cliente.", extensions={"code": "forbidden", "status": 403})
        if not self._cliente_id:
            return None
        try:
            return await info.context["loaders"]["clientes"].load(self._cliente_id)
        except ApiError as exc:
            raise fail(exc)


@strawberry.type
class PaginaPedidos:
    items: list[Pedido]
    total: int
    limite: int
    desplazamiento: int


@strawberry.type
class EstadoConteo:
    estado: str
    cantidad: int


@strawberry.type
class ProductoBajoStock:
    id: str
    nombre: str
    unidades_disponibles: int


@strawberry.type
class PanelOperacion:
    pedidos_por_estado: list[EstadoConteo]
    ventas_pagadas: int

    @strawberry.field(description="Inventory. Error parcial (campo null) si el rol no puede ver stock o inventory no responde.")
    async def productos_bajo_stock(self, info: strawberry.Info) -> Optional[list[ProductoBajoStock]]:
        try:
            low = (await inventory_api.acall("GET", "/internal/products/low-stock", identity=info.context["identity"]))["items"]
        except ApiError as exc:
            raise fail(exc)
        return [ProductoBajoStock(id=p["id"], nombre=p["nombre"], unidades_disponibles=p["disponible_unidades"]) for p in low]


@strawberry.type
class Yo:
    id: str
    rol: str
    perfil: Optional[Cliente]


def to_pedido(o: dict) -> Pedido:
    return Pedido(
        id=o["id"], estado=o["status"], total=o["total"], moneda=o["currency"], creado=o["created_at"],
        expira=o.get("expires_at"), estado_pago=o["payment"]["status"], requiere_reembolso=o["refund_required"],
        notas=o.get("notes"), cliente_ref=o.get("customer_ref"),
        lineas=[LineaPedido(producto_id=i["product_id"], nombre=i["nombre"], cantidad=i["qty"],
                            precio_unitario=i["unit_price"], subtotal=i["subtotal"]) for i in o["items"]],
        _cliente_id=o.get("customer_id"),
    )


def to_cliente(c: dict) -> Cliente:
    return Cliente(id=c["id"], nombre=c.get("nombre"), telefono=c.get("telefono"), direccion=c.get("direccion"))


# ------------------------------------------------------------------ consultas
@strawberry.type
class Query:
    @strawberry.field(description="Quién soy y mi perfil (clientes). Combina identidad verificada + clients.")
    async def yo(self, info: strawberry.Info) -> Yo:
        ident = info.context["identity"]
        perfil = None
        if ident.role == "customer":
            try:
                perfil = to_cliente(await clients_api.acall("GET", "/internal/clients/me", identity=ident))
            except ApiError as exc:
                if exc.status != 404:
                    raise fail(exc)
        return Yo(id=ident.user_id, rol=ident.role, perfil=perfil)

    @strawberry.field(description="Resumen de UN pedido: estado y montos (orders) + datos vigentes de producto (inventory).")
    async def resumen_pedido(self, info: strawberry.Info, id: strawberry.ID) -> Pedido:
        ident = info.context["identity"]
        try:
            data = await orders_api.acall("GET", f"/internal/orders/{id}", identity=ident)
        except ApiError as exc:
            raise fail(exc)  # 404 si el pedido es ajeno: la regla vive en orders
        return to_pedido(data)

    @strawberry.field(description="Pedidos paginados. Cliente: solo los suyos. Personal/auditoría: todos.")
    async def pedidos(self, info: strawberry.Info, primeros: int = 10, desplazamiento: int = 0,
                      estado: Optional[str] = None) -> PaginaPedidos:
        if not 1 <= primeros <= 50:
            raise GraphQLError("primeros debe estar entre 1 y 50.", extensions={"code": "validation_error", "status": 400})
        ident = info.context["identity"]
        params = {"limit": primeros, "offset": desplazamiento, **({"status": estado} if estado else {})}
        try:
            data = await orders_api.acall("GET", "/internal/orders", identity=ident, params=params)
        except ApiError as exc:
            raise fail(exc)
        return PaginaPedidos(items=[to_pedido(o) for o in data["items"]], total=data["total"],
                             limite=data["limit"], desplazamiento=data["offset"])

    @strawberry.field(description="Panel de operación: orders (conteos, ventas) + inventory (bajo stock).")
    async def panel_operacion(self, info: strawberry.Info) -> PanelOperacion:
        ident = info.context["identity"]
        if ident.role not in ("staff", "admin", "auditor"):
            raise GraphQLError("Tu rol no puede ver el panel.", extensions={"code": "forbidden", "status": 403})
        try:
            summary = await orders_api.acall("GET", "/internal/orders/summary", identity=ident)
        except ApiError as exc:
            raise fail(exc)
        return PanelOperacion(
            pedidos_por_estado=[EstadoConteo(estado=k, cantidad=v) for k, v in sorted(summary["by_status"].items())],
            ventas_pagadas=summary["paid_sales"],
        )


def mask(error: GraphQLError) -> bool:
    """Enmascara solo las excepciones inesperadas (podrían filtrar detalles internos).

    Los errores de validación/límites y los controlados con ``extensions.code`` se muestran tal cual."""
    original = error.original_error
    return original is not None and not isinstance(original, GraphQLError)


extensions = [
    QueryDepthLimiter(max_depth=int(os.getenv("LR_GQL_MAX_DEPTH", "6"))),
    MaxAliasesLimiter(max_alias_count=int(os.getenv("LR_GQL_MAX_ALIASES", "4"))),
    MaxTokensLimiter(max_token_count=int(os.getenv("LR_GQL_MAX_TOKENS", "600"))),
    MaskErrors(should_mask_error=mask),
]
if os.getenv("LR_GQL_INTROSPECTION", "0") != "1":
    extensions.append(DisableIntrospection())
schema = strawberry.Schema(query=Query, extensions=extensions)


async def _batch_products(ids: list[str]) -> list[Optional[Producto]]:
    data = await inventory_api.acall("POST", "/internal/products/batch", json={"ids": list(set(ids))})
    by_id = {p["id"]: Producto(id=p["id"], nombre=p["nombre"], emoji=p["emoji"], descripcion=p["descripcion"],
                               precio=p["precio"], disponible=p["disponible"]) for p in data["items"]}
    return [by_id.get(i) for i in ids]


def _clients_loader(identity):
    async def batch(ids: list[str]) -> list[Optional[Cliente]]:
        data = await clients_api.acall("POST", "/internal/clients/batch", identity=identity, json={"ids": list(set(ids))})
        by_id = {c["id"]: to_cliente(c) for c in data["items"]}
        return [by_id.get(i) for i in ids]
    return DataLoader(batch)


async def get_context(edge: Edge = Depends(guard)) -> dict:
    ident = edge.need_identity()
    # Un DataLoader por solicitud agrupa las N búsquedas de producto/cliente en UNA llamada.
    return {"identity": ident,
            "loaders": {"productos": DataLoader(_batch_products), "clientes": _clients_loader(ident)}}


app.include_router(GraphQLRouter(schema, path="/graphql", context_getter=get_context, graphql_ide=None, allow_queries_via_get=False))
