#!/usr/bin/env python3
"""Arranque LOCAL sin Docker (para desarrollo y para las pruebas automáticas).

Levanta los 7 servicios como procesos independientes. Diferencias con docker compose, a propósito:
  * Base de datos: mongomock en memoria por servicio (NO persiste). En compose se usa MongoDB real.
  * Secretos: modo "env". Se generan al azar en cada arranque y cada proceso recibe SOLO los que
    su política de Vault le entregaría (si un servicio pide un secreto que no le corresponde, falla,
    igual que fallaría contra Vault).
Uso:  python scripts/dev_local.py        (Ctrl+C para detener)
"""
from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
PORTS = {"gateway": 8000, "auth": 8001, "clients": 8002, "inventory": 8003, "orders": 8004, "payments": 8005, "graphql": 8006}
DIRS = {"graphql": "graphql_gateway"}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from topology import EDGES  # noqa: E402


def env_name(path: str, field: str) -> str:
    import re
    return "LR_SECRET__" + re.sub(r"[^A-Za-z0-9]", "_", path).upper() + "__" + field.upper()


class Stack:
    def __init__(self, overrides: dict | None = None, log_dir: Path | None = None):
        self.overrides = overrides or {}
        self.procs: dict[str, subprocess.Popen] = {}
        self.service_env: dict[str, dict] = {}
        self.seed_password = "Demo-" + secrets.token_urlsafe(9)
        self.webhook_secret = secrets.token_hex(24)
        self.edge_keys = {f"{a}__{b}": secrets.token_hex(24) for a, b in EDGES}
        self.log_dir = log_dir or ROOT / ".local-logs"
        self.base = f"http://127.0.0.1:{PORTS['gateway']}"

    def _env_for(self, name: str) -> dict:
        env = dict(os.environ)
        env.update({
            "PYTHONPATH": str(BACKEND / "common"), "LR_SECRETS_MODE": "env", "LR_DB_MODE": "mock", "LR_SEED": "1",
            "LR_SEED_PASSWORD": self.seed_password,
            "LR_ALLOWED_ORIGINS": "http://localhost:8080,http://127.0.0.1:8080",
            "LR_WEBHOOK_URL": f"http://127.0.0.1:{PORTS['gateway']}/api/v1/webhooks/payments",
            "LR_LOGIN_LOCK_SECONDS": "5",
        })
        for svc, port in PORTS.items():
            env[f"LR_{svc.upper()}_URL"] = f"http://127.0.0.1:{port}"
        for pair, key in self.edge_keys.items():
            a, b = pair.split("__")
            if name in (a, b):  # solo las aristas en las que participa este servicio
                env[env_name(f"edge/{pair}", "key")] = key
        if name == "payments":
            env[env_name("payments/webhook", "secret")] = self.webhook_secret
        env.update(self.overrides)
        env.update(self.service_env.get(name, {}))
        return env

    def _spawn(self, name: str) -> None:
        log = open(self.log_dir / f"{name}.log", "a")
        self.procs[name] = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--app-dir", str(BACKEND / DIRS.get(name, name)),
             "--host", "127.0.0.1", "--port", str(PORTS[name]), "--log-level", "warning"],
            env=self._env_for(name), stdout=log, stderr=subprocess.STDOUT)

    def stop_service(self, name: str) -> None:
        p = self.procs[name]
        p.terminate()
        p.wait(timeout=10)

    def start_service(self, name: str, timeout: float = 20.0, env: dict | None = None) -> None:
        self.service_env[name] = env or {}
        self._spawn(name)
        end = time.time() + timeout
        while time.time() < end:
            try:
                if httpx.get(f"http://127.0.0.1:{PORTS[name]}/health", timeout=1).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.3)
        raise RuntimeError(f"{name} no volvió a responder")

    def start(self, timeout: float = 40.0) -> "Stack":
        self.log_dir.mkdir(exist_ok=True)
        for old in self.log_dir.glob("*.log"):
            old.unlink()
        for name in PORTS:
            self._spawn(name)
        deadline = time.time() + timeout
        pending = set(PORTS)
        while pending and time.time() < deadline:
            for name in list(pending):
                try:
                    if httpx.get(f"http://127.0.0.1:{PORTS[name]}/health", timeout=1).status_code == 200:
                        pending.discard(name)
                except httpx.HTTPError:
                    pass
                if self.procs[name].poll() is not None:
                    raise RuntimeError(f"{name} terminó al arrancar; revisa {self.log_dir / (name + '.log')}")
            time.sleep(0.3)
        if pending:
            self.stop()
            raise RuntimeError(f"servicios sin responder: {sorted(pending)}")
        return self

    def stop(self) -> None:
        for p in self.procs.values():
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for p in self.procs.values():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    stack = Stack().start()
    info = {"gateway": stack.base, "usuarios": ["ana@ejemplo.cl", "beto@ejemplo.cl", "tienda@libreyrico.test",
                                                "admin@libreyrico.test", "auditoria@libreyrico.test"],
            "password_de_prueba": stack.seed_password}
    print(json.dumps(info, indent=2, ensure_ascii=False))
    print("\nBase en memoria (se pierde al detener). Ctrl+C para detener.")
    try:
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        stack.stop()
