"""Cliente de secretos en modo Vault, contra un Vault FALSO que imita la API KV v2.

Valida ruta, cabecera de token, permisos por política, caché, degradación con valor previo y fallo cerrado.
No sustituye una prueba contra Vault real (ver README: pendiente de ejecutar con docker compose).
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from lr_common.secrets import SecretUnavailable, SecretsProvider  # noqa: E402
from topology import vault_paths_for  # noqa: E402

DATA = {"edge/gateway__orders": {"key": "k-123"}, "db/orders": {"uri": "mongodb://x"}}
TOKENS = {"tok-orders": {"edge/gateway__orders"}}   # el token solo puede leer esa referencia


class FakeVault(BaseHTTPRequestHandler):
    hits = 0

    def log_message(self, *a): pass

    def do_GET(self):
        FakeVault.hits += 1
        if self.path == "/v1/sys/health":
            return self._send(200, {"initialized": True})
        ref = self.path.removeprefix("/v1/secret/data/lr/")
        allowed = TOKENS.get(self.headers.get("X-Vault-Token"))
        if allowed is None or ref not in allowed:
            return self._send(403, {"errors": ["permission denied"]})
        self._send(200, {"data": {"data": DATA[ref]}})

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)


@pytest.fixture()
def vault(monkeypatch, tmp_path):
    srv = HTTPServer(("127.0.0.1", 0), FakeVault)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tok = tmp_path / "token"; tok.write_text("tok-orders")
    monkeypatch.setenv("LR_SECRETS_MODE", "vault")
    monkeypatch.setenv("VAULT_ADDR", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setenv("VAULT_TOKEN_FILE", str(tok))
    FakeVault.hits = 0
    yield srv
    srv.shutdown()


def test_lee_secreto_con_token_del_servicio_y_cachea(vault):
    s = SecretsProvider()
    assert s.get("edge/gateway__orders", "key") == "k-123"
    assert s.get("edge/gateway__orders", "key") == "k-123"
    assert FakeVault.hits == 1                                     # segunda lectura sale de la caché


def test_politica_de_minimo_privilegio(vault):
    s = SecretsProvider()
    with pytest.raises(SecretUnavailable):
        s.get("db/orders", "uri")                                  # existe, pero el token no tiene permiso


def test_gestor_caido_usa_ultimo_valor_conocido_y_luego_falla_cerrado(vault, monkeypatch):
    monkeypatch.setenv("LR_SECRET_TTL", "0")                       # fuerza releer en cada uso
    monkeypatch.setenv("LR_SECRET_STALE_MAX", "1")
    s = SecretsProvider()
    assert s.get("edge/gateway__orders", "key") == "k-123"
    vault.shutdown(); vault.server_close()
    assert s.get("edge/gateway__orders", "key") == "k-123"         # degradación controlada (valor previo)
    time.sleep(1.2)
    with pytest.raises(SecretUnavailable):                         # pasado el plazo: fail closed
        s.get("edge/gateway__orders", "key")


def test_politicas_generadas_por_servicio():
    assert "edge/gateway__orders" in vault_paths_for("orders") and "db/orders" in vault_paths_for("orders")
    assert "db/orders" not in vault_paths_for("payments") and "payments/webhook" not in vault_paths_for("orders")
    assert vault_paths_for("gateway") == [f"edge/gateway__{d}" for d in ("auth", "clients", "inventory", "orders", "payments", "graphql")]
    assert not any(p.startswith("db/") for p in vault_paths_for("graphql") + vault_paths_for("gateway"))
