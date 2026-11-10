"""Acceso a secretos por referencia simbólica.

Los valores NUNCA viven en el código ni en el repositorio. Cada servicio pide
`secrets.get("edge/gateway__orders", "key")` y el proveedor decide de dónde sale:

* modo ``vault`` (por defecto, usado en docker compose): HashiCorp Vault, KV v2,
  con un token propio de cada servicio (política de mínimo privilegio).
* modo ``env`` (solo pruebas locales sin Docker): variables ``LR_SECRET__...``.

Si Vault no responde se usa el último valor conocido durante ``LR_SECRET_STALE_MAX``
segundos; pasado ese plazo se falla cerrado (503) en vez de operar sin credenciales.
"""
from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path

import httpx


class SecretUnavailable(Exception):
    """El secreto no se pudo obtener (gestor caído, referencia inexistente o sin permiso)."""


def env_name(path: str, field: str) -> str:
    return "LR_SECRET__" + re.sub(r"[^A-Za-z0-9]", "_", path).upper() + "__" + field.upper()


class SecretsProvider:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    # configuración leída en cada uso para que las pruebas puedan cambiarla
    @property
    def mode(self) -> str:
        return os.getenv("LR_SECRETS_MODE", "vault")

    def _token(self) -> str:
        token_file = os.getenv("VAULT_TOKEN_FILE")
        if token_file:
            try:
                return Path(token_file).read_text().strip()
            except OSError as exc:
                raise SecretUnavailable("token de Vault ilegible") from exc
        token = os.getenv("VAULT_TOKEN")
        if not token:
            raise SecretUnavailable("sin token de Vault configurado")
        return token

    def get(self, path: str, field: str) -> str:
        if self.mode == "env":
            value = os.environ.get(env_name(path, field))
            if not value:
                raise SecretUnavailable(f"referencia sin valor: {path}#{field}")
            return value
        data = self._vault_read(path)
        if field not in data:
            raise SecretUnavailable(f"campo inexistente en {path}")
        return str(data[field])

    def _vault_read(self, path: str) -> dict:
        ttl = int(os.getenv("LR_SECRET_TTL", "300"))
        stale_max = int(os.getenv("LR_SECRET_STALE_MAX", "900"))
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(path)
        if hit and now - hit[0] < ttl:
            return hit[1]
        addr = os.getenv("VAULT_ADDR", "http://vault:8200").rstrip("/")
        try:
            resp = httpx.get(
                f"{addr}/v1/secret/data/lr/{path}",
                headers={"X-Vault-Token": self._token()},
                timeout=float(os.getenv("LR_VAULT_TIMEOUT", "2")),
            )
            if resp.status_code != 200:
                raise SecretUnavailable(f"Vault respondió {resp.status_code} para {path}")
            data = resp.json()["data"]["data"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            if hit and now - hit[0] < stale_max:  # degradación controlada
                return hit[1]
            raise SecretUnavailable("gestor de secretos no disponible") from exc
        except SecretUnavailable:
            if hit and now - hit[0] < stale_max:
                return hit[1]
            raise
        with self._lock:
            self._cache[path] = (now, data)
        return data

    def ping(self) -> bool:
        """Para /ready: ¿se puede hablar con el gestor de secretos?"""
        if self.mode == "env":
            return True
        addr = os.getenv("VAULT_ADDR", "http://vault:8200").rstrip("/")
        try:
            return httpx.get(f"{addr}/v1/sys/health", timeout=2).status_code in (200, 429, 472, 473)
        except httpx.HTTPError:
            return False


secrets = SecretsProvider()
