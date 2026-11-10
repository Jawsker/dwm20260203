"""Tabla explícita de rutas del API Gateway: única fuente de verdad.

Lo que no está aquí NO se enruta (404). No hay "proxy genérico" a /internal/*.
De esta tabla se genera la matriz de rutas de la documentación (scripts/generar_matriz.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

PREFIX = "/api/v1"
ANY = ("customer", "staff", "admin", "auditor")


@dataclass(frozen=True)
class Route:
    id: str                      # S01... (trazabilidad con el Módulo 1)
    method: str
    path: str                    # ruta externa, con {parametros}
    upstream: Optional[str]      # servicio privado destino (None = lo resuelve un handler)
    target: str                  # ruta interna de destino
    auth: str = "session"        # "none" | "session"
    roles: tuple = ANY           # roles permitidos (si auth == "session")
    rate: str = "auth"           # clase de límite de solicitudes
    body_max: int = 4096         # bytes máximos de cuerpo
    query: tuple = ()            # parámetros de consulta permitidos (el resto se descarta)
    forward: tuple = ()          # cabeceras del navegador que sí se reenvían
    identity: bool = True        # ¿se propaga la identidad verificada al servicio?
    handler: Optional[str] = None  # orquestación propia del gateway
    timeout: float = 5.0
    cred: str = ""               # referencia simbólica de la credencial usada en el tramo interno
    controls: str = ""


ROUTES: list[Route] = [
    Route("S01", "GET", "/products", "inventory", "/internal/products", auth="none", rate="public",
          query=("categoria", "q", "available", "limit", "offset"), identity=False, cred="edge/gateway__inventory",
          controls="filtros validados (400), paginación acotada, solo campos de catálogo"),
    Route("S02", "GET", "/products/{product_id}", "inventory", "/internal/products/{product_id}", auth="none",
          rate="public", identity=False, cred="edge/gateway__inventory", controls="id acotado a [A-Za-z0-9_.-]{1,80}"),
    Route("S03", "POST", "/auth/register", None, "", auth="none", rate="login", handler="register", body_max=1024,
          cred="edge/gateway__auth, edge/gateway__clients", controls="el rol nunca viene del cliente; compensación si falla clients"),
    Route("S04", "POST", "/auth/login", None, "", auth="none", rate="login", handler="login", body_max=512,
          cred="edge/gateway__auth", controls="bloqueo por intentos, cookie HttpOnly, token jamás en el cuerpo"),
    Route("S05", "POST", "/auth/logout", None, "", rate="auth", handler="logout", body_max=0, cred="edge/gateway__auth",
          controls="revocación inmediata de la sesión"),
    Route("S06", "GET", "/auth/session", None, "", rate="auth", handler="session", cred="edge/gateway__auth"),
    Route("S07", "GET", "/clients/me", "clients", "/internal/clients/me", roles=("customer",), cred="edge/gateway__clients",
          controls="el id sale de la sesión, no de la URL"),
    Route("S08", "PUT", "/clients/me", "clients", "/internal/clients/me", roles=("customer",), body_max=1024,
          cred="edge/gateway__clients", controls="solo campos permitidos; validación en el servicio"),
    Route("S09", "DELETE", "/account", None, "", roles=("customer",), handler="delete_account", body_max=0,
          cred="edge/gateway__orders, edge/gateway__clients, edge/gateway__auth", controls="elimina perfil y credenciales; anonimiza pedidos"),
    Route("S10", "POST", "/contact", "clients", "/internal/contact", auth="none", rate="contact", body_max=2048,
          identity=False, cred="edge/gateway__clients", controls="límite estricto por IP"),
    Route("S11", "GET", "/admin/contact", "clients", "/internal/contact", roles=("staff", "admin"), query=("limit",),
          cred="edge/gateway__clients"),
    Route("S12", "POST", "/orders", "orders", "/internal/orders", roles=("customer",), rate="write", body_max=4096,
          forward=("idempotency-key",), cred="edge/gateway__orders", controls="precios y total los calcula el servidor; Idempotency-Key"),
    Route("S13", "GET", "/orders/{order_id}", "orders", "/internal/orders/{order_id}", cred="edge/gateway__orders",
          controls="propiedad del pedido verificada en orders (404 si es ajeno)"),
    Route("S14", "POST", "/orders/{order_id}/pay", "orders", "/internal/orders/{order_id}/pay", roles=("customer",),
          rate="write", body_max=0, cred="edge/gateway__orders", timeout=8.0, controls="monto tomado del pedido guardado"),
    Route("S15", "POST", "/orders/{order_id}/cancel", "orders", "/internal/orders/{order_id}/cancel",
          roles=("customer", "staff", "admin"), rate="write", body_max=0, cred="edge/gateway__orders"),
    Route("S16", "POST", "/admin/orders/{order_id}/status", "orders", "/internal/orders/{order_id}/status",
          roles=("staff", "admin"), rate="write", body_max=256, cred="edge/gateway__orders", controls="máquina de estados en orders"),
    Route("S17", "GET", "/payments/{provider_ref}", "payments", "/internal/payments/by-ref/{provider_ref}",
          roles=("customer",), cred="edge/gateway__payments", controls="solo el dueño del pago"),
    Route("S18", "POST", "/payments/{provider_ref}/sandbox-decision", "payments", "/internal/sandbox/{provider_ref}/decide",
          roles=("customer",), rate="write", body_max=128, timeout=10.0, cred="edge/gateway__payments",
          controls="simula la pantalla del proveedor; NO confirma el pago (lo hace el webhook firmado)"),
    Route("S19", "POST", "/webhooks/payments", "payments", "/internal/webhooks/provider", auth="none", rate="webhook",
          body_max=2048, forward=("x-provider-signature", "content-type"), identity=False, cred="edge/gateway__payments + payments/webhook",
          controls="firma HMAC con marca de tiempo, event_id único, verificación de monto"),
    Route("S20", "POST", "/graphql", "graphql", "/graphql", rate="auth", body_max=4096, timeout=8.0,
          cred="edge/gateway__graphql", controls="límites de profundidad/alias/tokens; autorización por campo en cada servicio"),
    Route("S21", "GET", "/admin/products", "inventory", "/internal/products", roles=("staff", "admin"),
          query=("categoria", "q", "limit", "offset"), cred="edge/gateway__inventory", controls="incluye stock (vista de personal)"),
    Route("S22", "POST", "/admin/products", "inventory", "/internal/products", roles=("admin",), body_max=1024,
          cred="edge/gateway__inventory"),
    Route("S23", "PUT", "/admin/products/{product_id}", "inventory", "/internal/products/{product_id}", roles=("admin",),
          body_max=1024, cred="edge/gateway__inventory"),
    Route("S24", "PUT", "/admin/products/{product_id}/stock", "inventory", "/internal/products/{product_id}/stock",
          roles=("staff", "admin"), body_max=128, cred="edge/gateway__inventory"),
    Route("S25", "POST", "/admin/users", "auth", "/internal/users", roles=("admin",), body_max=512, cred="edge/gateway__auth",
          controls="crea personal/auditoría; solo administración"),
    Route("S26", "POST", "/admin/maintenance/sweep", "orders", "/internal/orders/maintenance/sweep", roles=("admin",),
          body_max=0, cred="edge/gateway__orders", controls="expira pedidos y libera stock"),
]
