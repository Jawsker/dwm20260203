"""API Gateway (único servicio con puerto público junto al frontend).

Qué hace, en orden, con cada solicitud:
 1. Busca la ruta en la tabla explícita (routes.py). Desconocida → 404; verbo no permitido → 405.
 2. Límite de solicitudes por clase de ruta e IP → 429.
 3. Tamaño de cuerpo y tipo de contenido → 413/415.
 4. Si la ruta exige sesión: lee la cookie HttpOnly, la valida con Auth (introspección) → 401.
    El rol se comprueba aquí → 403 (y otra vez en el servicio destino: defensa en profundidad).
 5. Origen (CSRF) en verbos que cambian estado → 403.
 6. DESCARTA todas las cabeceras del navegador salvo una lista corta, y reenvía solo contexto
    verificado (X-Auth-User/X-Auth-Role) con la clave de arista del gateway.
 7. Traduce fallos: destino sin respuesta a tiempo 504, caído 503, error interno 502.
"""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from lr_common.client import ServiceClient
from lr_common.logs import correlation_id
from lr_common.web import ApiError, Identity, create_app
from routes import PREFIX, ROUTES, Route

SERVICE = "gateway"
app = create_app(SERVICE)

SERVICES = {
    name: ServiceClient(SERVICE, name, f"LR_{name.upper()}_URL", f"http://{name}:8000", timeout=4.0)
    for name in ("auth", "clients", "inventory", "orders", "payments", "graphql")
}
COOKIE = "lr_session"
COOKIE_SECURE = os.getenv("LR_COOKIE_SECURE", "0") == "1"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("LR_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",") if o.strip()]
UNSAFE = {"POST", "PUT", "DELETE", "PATCH"}

# --------------------------------------------------------------- límite de solicitudes (ventana deslizante)
RATE = {  # solicitudes por minuto e IP; configurable por variable LR_RATE_<CLASE>
    "public": int(os.getenv("LR_RATE_PUBLIC", "240")), "auth": int(os.getenv("LR_RATE_AUTH", "300")),
    "write": int(os.getenv("LR_RATE_WRITE", "60")), "login": int(os.getenv("LR_RATE_LOGIN", "20")),
    "contact": int(os.getenv("LR_RATE_CONTACT", "5")), "webhook": int(os.getenv("LR_RATE_WEBHOOK", "120")),
}
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def rate_limit(klass: str, ip: str) -> None:
    now, window = time.monotonic(), 60.0
    q = _hits[(klass, ip)]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= RATE[klass]:
        retry = max(1, int(window - (now - q[0])))
        raise ApiError(429, "rate_limited", f"Demasiadas solicitudes. Reintenta en {retry} s.", [{"retry_after": retry}])
    q.append(now)


# --------------------------------------------------------------- tabla de rutas
def _compile(r: Route) -> re.Pattern:
    return re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[A-Za-z0-9_.-]{1,80})", PREFIX + r.path) + "$")


TABLE = [(r, _compile(r)) for r in ROUTES]


def match(method: str, path: str) -> tuple[Optional[Route], dict, list[str]]:
    allowed = []
    for r, rx in TABLE:
        m = rx.match(path)
        if m:
            if r.method == method:
                return r, m.groupdict(), []
            allowed.append(r.method)
    return None, {}, allowed


# --------------------------------------------------------------- sesión
async def current_identity(request: Request) -> tuple[Optional[Identity], Optional[str], Optional[str]]:
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 200:
        return None, None, None
    data = await SERVICES["auth"].acall("POST", "/internal/introspect", json={"token": token})
    if not data.get("active"):
        return None, token, None
    return Identity(data["user_id"], data["role"]), token, data.get("email")


def set_cookie(resp: Response, token: str, max_age: int) -> None:
    resp.set_cookie(COOKIE, token, max_age=max_age, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/")


def clear_cookie(resp: Response) -> None:
    resp.delete_cookie(COOKIE, path="/", httponly=True, samesite="lax", secure=COOKIE_SECURE)


def check_origin(request: Request, route: Route, has_cookie: bool) -> None:
    if request.method not in UNSAFE or route.id == "S19":
        return
    origin = request.headers.get("origin")
    if origin is None:
        ref = request.headers.get("referer", "")
        m = re.match(r"^(https?://[^/]+)", ref)
        origin = m.group(1) if m else None
    if origin is None:
        if route.auth == "session" or has_cookie:  # petición con cookie sin origen verificable
            raise ApiError(403, "csrf_origin", "Origen de la solicitud no verificable.")
        return
    if origin not in ALLOWED_ORIGINS:
        raise ApiError(403, "csrf_origin", "Origen no permitido.")


# --------------------------------------------------------------- orquestaciones propias
class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10, max_length=128)
    nombre: str = Field(min_length=2, max_length=80)
    telefono: Optional[str] = Field(default=None, pattern=r"^\+?[0-9 ]{8,15}$")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=128)


def parse(model, body: bytes):
    try:
        return model.model_validate_json(body)
    except ValidationError as exc:
        details = [{"field": ".".join(str(p) for p in e["loc"]), "reason": e["type"]} for e in exc.errors()]
        raise ApiError(400, "validation_error", "La solicitud no cumple el contrato.", details)


async def _login(email: str, password: str) -> JSONResponse:
    res = await SERVICES["auth"].acall("POST", "/internal/login", json={"email": email, "password": password})
    resp = JSONResponse({"user": res["user"]})
    set_cookie(resp, res["token"], res["max_age"])  # el token viaja solo en cookie HttpOnly
    return resp


async def h_register(request, route, body, ident, token, email):
    data = parse(RegisterIn, body)
    created = await SERVICES["auth"].acall("POST", "/internal/register", json={"email": data.email, "password": data.password})
    try:
        await SERVICES["clients"].acall("POST", "/internal/clients", json={
            "user_id": created["user_id"], "nombre": data.nombre, "telefono": data.telefono})
    except ApiError:
        # compensación: no dejar una cuenta sin perfil
        try:
            await SERVICES["auth"].acall("DELETE", f"/internal/users/{created['user_id']}")
        finally:
            pass
        raise
    resp = await _login(data.email, data.password)
    resp.status_code = 201
    return resp


async def h_login(request, route, body, ident, token, email):
    data = parse(LoginIn, body)
    return await _login(data.email, data.password)


async def h_logout(request, route, body, ident, token, email):
    await SERVICES["auth"].acall("POST", "/internal/logout", json={"token": token})
    resp = Response(status_code=204)
    clear_cookie(resp)
    return resp


async def h_session(request, route, body, ident, token, email):
    return JSONResponse({"user_id": ident.user_id, "role": ident.role, "email": email})


async def h_delete_account(request, route, body, ident, token, email):
    await SERVICES["orders"].acall("POST", "/internal/orders/anonymize", identity=ident, json={"user_id": ident.user_id})
    await SERVICES["clients"].acall("DELETE", "/internal/clients/me", identity=ident)
    await SERVICES["auth"].acall("DELETE", f"/internal/users/{ident.user_id}", identity=ident)
    resp = Response(status_code=204)
    clear_cookie(resp)
    return resp


HANDLERS = {"register": h_register, "login": h_login, "logout": h_logout, "session": h_session,
            "delete_account": h_delete_account}
ALLOWED_FORWARD = {"content-type", "idempotency-key", "x-provider-signature"}


def _controlled_failure(upstream) -> bool:
    """503/504/502 con cuerpo de error propio = un servicio informó que SU dependencia falló; se conserva el código."""
    if upstream.status_code not in (502, 503, 504):
        return False
    try:
        return "code" in upstream.json()["error"]
    except (ValueError, KeyError, TypeError):
        return False


# --------------------------------------------------------------- despacho
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], include_in_schema=False)
async def dispatch(request: Request, full_path: str):
    path = "/" + full_path
    route, params, allowed = match(request.method, path)
    if route is None:
        if allowed:
            raise_405 = JSONResponse({"error": {"code": "method_not_allowed", "message": "Verbo no permitido.",
                                                "correlation_id": correlation_id.get()}}, status_code=405,
                                     headers={"Allow": ", ".join(sorted(set(allowed)))})
            return raise_405
        raise ApiError(404, "not_found", "Ruta inexistente.")

    ip = request.client.host if request.client else "unknown"
    rate_limit(route.rate, ip)

    body = b""
    if request.method in UNSAFE:
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > route.body_max:
            raise ApiError(413, "payload_too_large", "Cuerpo demasiado grande.")
        body = await request.body()
        if len(body) > route.body_max:
            raise ApiError(413, "payload_too_large", "Cuerpo demasiado grande.")
        if body and "application/json" not in request.headers.get("content-type", ""):
            raise ApiError(415, "unsupported_media_type", "Se requiere application/json.")

    ident = token = email = None
    has_cookie = COOKIE in request.cookies
    check_origin(request, route, has_cookie)
    if route.auth == "session":
        ident, token, email = await current_identity(request)
        if ident is None:
            resp = JSONResponse({"error": {"code": "unauthenticated", "message": "Inicia sesión para continuar.",
                                           "correlation_id": correlation_id.get()}}, status_code=401)
            if token:
                clear_cookie(resp)
            return resp
        if ident.role not in route.roles:
            raise ApiError(403, "forbidden", "Tu rol no permite esta operación.")

    if route.handler:
        return await HANDLERS[route.handler](request, route, body, ident, token, email)

    # ---- reenvío al servicio privado con contexto verificado ----
    target = route.target.format(**params)
    query = {k: v for k, v in request.query_params.items() if k in route.query}
    fwd = {k: v for k, v in ((h, request.headers.get(h)) for h in route.forward) if v and k in ALLOWED_FORWARD}
    if body:
        fwd["content-type"] = "application/json"  # ya validado arriba; no se reenvía lo que diga el navegador
    upstream = await SERVICES[route.upstream].araw(
        request.method, target, identity=ident if route.identity else None,
        content=body or None, params=query or None, headers=fwd, timeout=route.timeout)
    if upstream.status_code >= 500 and not _controlled_failure(upstream):
        raise ApiError(502, "upstream_error", "Un servicio interno falló.")
    out = Response(content=upstream.content, status_code=upstream.status_code,
                   media_type="application/json" if upstream.content else None)
    if route.auth == "session":
        out.headers["Cache-Control"] = "no-store"
    return out


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Cache-Control", "no-store")
    return resp


app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Idempotency-Key"],
                   expose_headers=["X-Correlation-Id"], max_age=600)
