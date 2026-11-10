#!/usr/bin/env python3
"""Inicializa secretos y accesos mínimos (se ejecuta UNA vez por arranque, dentro de la red privada).

1. Crea en MongoDB un usuario por servicio con permiso readWrite SOLO sobre su base.
2. Genera credenciales al azar y las guarda en Vault (KV v2) bajo referencias simbólicas:
     lr/db/<servicio>            uri de conexión (formato connectionstrings.com para MongoDB)
     lr/edge/<llamador>__<dest>  clave de servicio por arista
     lr/payments/webhook         secreto de firma del proveedor de pagos (sandbox)
3. Crea una política de solo lectura por servicio y un token por servicio, escrito en el volumen
   que SOLO ese servicio monta. Ningún servicio puede leer secretos de otro.
Es idempotente: reutiliza lo que ya existe en Vault y actualiza la clave del usuario Mongo si cambió.
El token raíz de Vault solo lo recibe este contenedor. En producción: AppRole/identidad de plataforma
en lugar de tokens de larga vida, y Vault real (no modo dev) con sellado y auditoría.
"""
import os
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from pymongo import MongoClient
from pymongo.errors import OperationFailure

sys.path.insert(0, str(Path(__file__).resolve().parent))
from topology import EDGES, SERVICES, WITH_DB, vault_paths_for  # noqa: E402

VAULT = os.environ.get("VAULT_ADDR", "http://vault:8200").rstrip("/")
ROOT_TOKEN = os.environ["VAULT_ROOT_TOKEN"]
MONGO_HOST = os.environ.get("MONGO_HOST", "mongo")
TOKEN_DIR = Path(os.environ.get("TOKEN_DIR", "/run/tokens"))
H = {"X-Vault-Token": ROOT_TOKEN}


def vault(method, path, **kw):
    r = httpx.request(method, f"{VAULT}/v1/{path}", headers=H, timeout=10, **kw)
    if r.status_code >= 400 and not (method == "GET" and r.status_code == 404):
        raise SystemExit(f"Vault {method} {path} -> {r.status_code}")
    return r


def read_secret(ref):
    r = vault("GET", f"secret/data/lr/{ref}")
    return r.json()["data"]["data"] if r.status_code == 200 else None


def write_secret(ref, data):
    vault("POST", f"secret/data/lr/{ref}", json={"data": data})


def wait_vault():
    for _ in range(60):
        try:
            if httpx.get(f"{VAULT}/v1/sys/health", timeout=2).status_code in (200, 429, 472, 473):
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise SystemExit("Vault no responde")


def main():
    wait_vault()
    mongo = MongoClient(f"mongodb://{quote_plus(os.environ['MONGO_ROOT_USER'])}:{quote_plus(os.environ['MONGO_ROOT_PASSWORD'])}"
                        f"@{MONGO_HOST}:27017/?authSource=admin", serverSelectionTimeoutMS=30000)
    mongo.admin.command("ping")

    for svc in WITH_DB:
        existing = read_secret(f"db/{svc}")
        password = existing["password"] if existing else secrets.token_urlsafe(24)
        db = mongo[svc]
        try:
            db.command("createUser", f"svc_{svc}", pwd=password, roles=[{"role": "readWrite", "db": svc}])
        except OperationFailure:  # ya existe: se alinea la clave con la de Vault
            db.command("updateUser", f"svc_{svc}", pwd=password)
        uri = f"mongodb://svc_{svc}:{quote_plus(password)}@{MONGO_HOST}:27017/{svc}?authSource={svc}"
        write_secret(f"db/{svc}", {"uri": uri, "password": password})

    for a, b in EDGES:
        ref = f"edge/{a}__{b}"
        if not read_secret(ref):
            write_secret(ref, {"key": secrets.token_hex(32)})
    if not read_secret("payments/webhook"):
        write_secret("payments/webhook", {"secret": secrets.token_hex(32)})

    for svc in SERVICES:
        rules = "\n".join(f'path "secret/data/lr/{p}" {{ capabilities = ["read"] }}' for p in vault_paths_for(svc))
        vault("PUT", f"sys/policies/acl/lr-{svc}", json={"policy": rules})
        tok = vault("POST", "auth/token/create", json={"policies": [f"lr-{svc}"], "ttl": "720h", "no_parent": True,
                                                       "display_name": svc}).json()["auth"]["client_token"]
        d = TOKEN_DIR / svc
        d.mkdir(parents=True, exist_ok=True)
        (d / "token").write_text(tok)
        os.chmod(d / "token", 0o444)  # lectura solo para el contenedor que monta ESTE volumen
        print(f"  política lr-{svc}: {len(vault_paths_for(svc))} referencias de lectura")
    print("bootstrap listo")


if __name__ == "__main__":
    main()
