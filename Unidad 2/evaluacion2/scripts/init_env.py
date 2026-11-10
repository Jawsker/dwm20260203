#!/usr/bin/env python3
"""Crea deploy/.env con valores aleatorios la primera vez (el archivo NO se versiona)."""
import secrets
from pathlib import Path

env = Path(__file__).resolve().parent.parent / "deploy" / ".env"
if env.exists():
    print(f"{env} ya existe; no se modifica.")
else:
    env.write_text(
        "# Generado por scripts/init_env.py. NO subir a git.\n"
        "MONGO_ROOT_USER=lr_root\n"
        f"MONGO_ROOT_PASSWORD={secrets.token_urlsafe(24)}\n"
        f"VAULT_ROOT_TOKEN={secrets.token_urlsafe(24)}\n"
        f"LR_SEED_PASSWORD=Demo-{secrets.token_urlsafe(9)}\n"
        "LR_ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080\n"
        "LR_COOKIE_SECURE=0\n"
        "LR_API_BASE=http://localhost:8000\n")
    print(f"creado {env}")
