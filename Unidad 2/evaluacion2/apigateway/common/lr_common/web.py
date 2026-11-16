"""Base HTTP de los servicios: errores uniformes, correlación, health y verificación de borde.

Verificación de borde ("edge"): ningún servicio privado confía en la red. Cada llamada
interna lleva ``X-Edge-Caller`` + ``X-Edge-Key``. La clave es un secreto POR ARISTA
(``edge/<llamador>__<destino>``) guardado en el gestor de secretos; el destino solo
conoce las claves de los llamadores que su contrato permite. La identidad del usuario
(``X-Auth-User``/``X-Auth-Role``) solo se acepta si el llamador verificado es un
propagador de identidad (gateway o graphql).
"""
from __future__ import annotations

import hmac
import re
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logs import correlation_id, setup_logging
from .secrets import SecretUnavailable, secrets

ROLES = ("customer", "staff", "admin", "auditor")
_CID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Optional[list] = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


@dataclass(frozen=True)
class Identity:
    user_id: str
    role: str

    def require(self, *roles: str) -> "Identity":
        if self.role not in roles:
            raise ApiError(403, "forbidden", "Tu rol no permite esta operación.")
        return self

    @property
    def is_staff(self) -> bool:
        return self.role in ("staff", "admin")


@dataclass(frozen=True)
class Edge:
    caller: str
    identity: Optional[Identity]

    def need_identity(self) -> Identity:
        if self.identity is None:
            raise ApiError(401, "identity_required", "Falta identidad de usuario verificada.")
        return self.identity


def edge_guard(me: str, allowed: Iterable[str], identity_from: Iterable[str] = ()) -> Callable[[Request], Edge]:
    allowed, identity_from = tuple(allowed), tuple(identity_from)

    def dependency(request: Request) -> Edge:
        caller = request.headers.get("x-edge-caller", "")
        presented = request.headers.get("x-edge-key", "")
        if caller not in allowed or not presented:
            raise ApiError(401, "edge_unauthorized", "Acceso directo sin identidad de servicio autorizada.")
        try:
            expected = secrets.get(f"edge/{caller}__{me}", "key")
        except SecretUnavailable as exc:
            raise ApiError(503, "secrets_unavailable", "Gestor de secretos no disponible.") from exc
        if not hmac.compare_digest(presented.encode(), expected.encode()):  # tiempo constante
            raise ApiError(401, "edge_unauthorized", "Acceso directo sin identidad de servicio autorizada.")
        ident = None
        if caller in identity_from:
            uid, role = request.headers.get("x-auth-user"), request.headers.get("x-auth-role")
            if uid and role in ROLES:
                ident = Identity(uid, role)
        return Edge(caller, ident)

    return dependency


def new_cid() -> str:
    return uuid.uuid4().hex[:16]


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "correlation_id": correlation_id.get()}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status)


def create_app(service: str, *, ready_checks: Optional[dict[str, Callable[[], bool]]] = None, **kwargs) -> FastAPI:
    log = setup_logging(service)
    app = FastAPI(title=f"Libre & Rico — {service}", docs_url=None, redoc_url=None, openapi_url=None, **kwargs)
    app.state.log = log

    @app.middleware("http")
    async def correlation_and_access_log(request: Request, call_next):
        incoming = request.headers.get("x-correlation-id", "")
        cid = incoming if _CID_RE.match(incoming) else new_cid()
        token = correlation_id.set(cid)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-Id"] = cid
            return response
        finally:
            route = request.scope.get("route")
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "route": getattr(route, "path", "(sin ruta)"),
                    "status": status,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            correlation_id.reset(token)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _error(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # Nunca se devuelve el valor recibido (podría ser una clave): solo campo y motivo.
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "reason": e["type"]} for e in exc.errors()]
        return _error(400, "validation_error", "La solicitud no cumple el contrato.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _error(exc.status_code, code, "Recurso o método no disponible.")

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.error("unhandled", exc_info=(type(exc), exc, None))
        return _error(500, "internal_error", "Error interno. Indica el identificador de correlación al soporte.")

    @app.get("/health", include_in_schema=False)
    def health():
        return {"status": "ok", "service": service}

    @app.get("/ready", include_in_schema=False)
    def ready():
        checks = {"secrets": secrets.ping, **(ready_checks or {})}
        results = {}
        for name, fn in checks.items():
            try:
                results[name] = bool(fn())
            except Exception:  # noqa: BLE001
                results[name] = False
        ok = all(results.values())
        return JSONResponse({"status": "ready" if ok else "degraded", "checks": results}, status_code=200 if ok else 503)

    return app
