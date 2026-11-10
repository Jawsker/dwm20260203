"""Cliente HTTP para llamadas internas servicio→servicio.

* Identidad de servicio por arista (``edge/<yo>__<destino>``), nunca la sesión del usuario.
* Propaga la identidad ya verificada (``X-Auth-User``/``X-Auth-Role``) y la correlación.
* Plazos máximos explícitos. Errores traducidos: sin respuesta a tiempo → 504, sin conexión → 503,
  fallo interno del destino → 502. Los errores de negocio 4xx se propagan con su código.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from .logs import correlation_id
from .secrets import SecretUnavailable, secrets
from .web import ApiError, Identity


# Sin conexiones persistentes: si un servicio se reinicia (despliegue, caída), no quedan sockets muertos
# que hagan fallar la primera solicitud de un POST no idempotente. Costo: un handshake TCP local por llamada.
_LIMITS = httpx.Limits(max_keepalive_connections=0)


class ServiceClient:
    def __init__(self, me: str, callee: str, url_env: str, default_url: str, timeout: float = 3.0):
        self.me, self.callee, self.timeout = me, callee, timeout
        self.url_env, self.default_url = url_env, default_url
        self._sync: Optional[httpx.Client] = None
        self._async: Optional[httpx.AsyncClient] = None

    @property
    def base(self) -> str:
        return os.getenv(self.url_env, self.default_url).rstrip("/")

    def _headers(self, identity: Optional[Identity], extra: Optional[dict]) -> dict:
        try:
            key = secrets.get(f"edge/{self.me}__{self.callee}", "key")
        except SecretUnavailable as exc:
            raise ApiError(503, "secrets_unavailable", "Gestor de secretos no disponible.") from exc
        headers = {"X-Edge-Caller": self.me, "X-Edge-Key": key, "X-Correlation-Id": correlation_id.get()}
        if identity:
            headers["X-Auth-User"], headers["X-Auth-Role"] = identity.user_id, identity.role
        if extra:
            headers.update(extra)
        return headers

    def _fail(self, exc: Exception) -> ApiError:
        if isinstance(exc, httpx.TimeoutException):
            return ApiError(504, "upstream_timeout", f"El servicio {self.callee} no respondió a tiempo.")
        return ApiError(503, "upstream_unavailable", f"El servicio {self.callee} no está disponible.")

    def _result(self, resp: httpx.Response) -> Any:
        if resp.status_code >= 500:
            raise ApiError(502, "upstream_error", f"El servicio {self.callee} falló.")
        if resp.status_code >= 400:
            try:
                err = resp.json()["error"]
                raise ApiError(resp.status_code, err["code"], err["message"], err.get("details"))
            except (ValueError, KeyError, TypeError):
                raise ApiError(502, "upstream_error", f"Respuesta inválida de {self.callee}.")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ---- sincrónico (servicios con endpoints `def`) ----
    def call(self, method: str, path: str, *, identity: Optional[Identity] = None, json: Any = None,
             params: Optional[dict] = None, headers: Optional[dict] = None, timeout: Optional[float] = None) -> Any:
        if self._sync is None:
            self._sync = httpx.Client(limits=_LIMITS)
        try:
            resp = self._sync.request(method, self.base + path, headers=self._headers(identity, headers),
                                      json=json, params=params, timeout=timeout or self.timeout)
        except httpx.HTTPError as exc:
            raise self._fail(exc) from exc
        return self._result(resp)

    # ---- asincrónico (GraphQL y gateway) ----
    async def acall(self, method: str, path: str, *, identity: Optional[Identity] = None, json: Any = None,
                    params: Optional[dict] = None, headers: Optional[dict] = None, timeout: Optional[float] = None) -> Any:
        if self._async is None:
            self._async = httpx.AsyncClient(limits=_LIMITS)
        try:
            resp = await self._async.request(method, self.base + path, headers=self._headers(identity, headers),
                                             json=json, params=params, timeout=timeout or self.timeout)
        except httpx.HTTPError as exc:
            raise self._fail(exc) from exc
        return self._result(resp)

    async def araw(self, method: str, path: str, *, identity: Optional[Identity], content: bytes | None,
                   params: Optional[dict], headers: dict, timeout: float) -> httpx.Response:
        """Para el API Gateway: reenvía bytes tal cual y devuelve la respuesta sin interpretarla."""
        if self._async is None:
            self._async = httpx.AsyncClient(limits=_LIMITS)
        try:
            return await self._async.request(method, self.base + path, headers=self._headers(identity, headers),
                                             content=content, params=params, timeout=timeout)
        except httpx.HTTPError as exc:
            raise self._fail(exc) from exc
