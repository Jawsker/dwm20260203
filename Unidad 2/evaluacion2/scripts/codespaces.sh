#!/usr/bin/env bash
# Levanta todo el sistema con Docker dentro de un GitHub Codespace.
#   bash "Unidad 2/evaluacion2/scripts/codespaces.sh"
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${CODESPACE_NAME:-}" ]; then
  echo "Este script es para GitHub Codespaces. En tu PC usa: docker compose -f deploy/docker-compose.yml up --build" >&2
  exit 1
fi

SITIO="https://${CODESPACE_NAME}-8080.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"

[ -f deploy/.env ] || python3 scripts/init_env.py

# El sitio y la API se sirven desde la misma dirección pública del Codespace (HTTPS).
python3 - "$SITIO" <<'PY'
import sys, re, pathlib
sitio = sys.argv[1]
p = pathlib.Path("deploy/.env")
s = p.read_text(encoding="utf-8")
for clave, valor in {"LR_API_BASE": sitio, "LR_ALLOWED_ORIGINS": sitio, "LR_COOKIE_SECURE": "1"}.items():
    if re.search(rf"^{clave}=.*$", s, flags=re.M):
        s = re.sub(rf"^{clave}=.*$", f"{clave}={valor}", s, flags=re.M)
    else:
        s += f"\n{clave}={valor}"
p.write_text(s.rstrip("\n") + "\n", encoding="utf-8")
PY

docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.codespaces.yml up --build -d
echo
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.codespaces.yml ps
echo
echo "Sitio:    ${SITIO}/productos.php"
echo "Usuarios: ana@ejemplo.cl · beto@ejemplo.cl · tienda@libreyrico.test · admin@libreyrico.test · auditoria@libreyrico.test"
grep '^LR_SEED_PASSWORD=' deploy/.env | sed 's/^LR_SEED_PASSWORD=/Contraseña de prueba: /'
echo
echo "Logs legibles (en otra terminal):"
echo "  cd \"$(pwd)\" && docker compose -f deploy/docker-compose.yml logs -f gateway auth orders inventory | python3 scripts/ver_logs.py"
