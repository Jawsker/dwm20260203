# Libre & Rico · Evaluación 2 · Backend seguro completo

Sitio web de la panadería sin gluten Libre & Rico con un backend de **7 servicios** (FastAPI + MongoDB + Vault), integrado al front-end PHP/Bootstrap. **¿Primera vez? Empieza por [`docs/GUIA-PARA-ENTENDER.md`](docs/GUIA-PARA-ENTENDER.md)** (explicación simple). El informe por módulo está en [`docs/INFORME.md`](docs/INFORME.md).

```
Navegador ──► API Gateway (8000) ──► auth · clients · inventory · orders · payments · graphql   (red privada)
                                         └─► MongoDB (una base y un usuario por servicio) · Vault (secretos)
```

## Estado de verificación (leer primero)

| Qué | Estado |
|---|---|
| Servicios, reglas de negocio, seguridad | **Probado**: pruebas automatizadas contra los 7 procesos reales (`pytest tests`) |
| Front-end integrado | **Probado** con Playwright (script `tests/browser_e2e.py`, capturas en `docs/evidencia/capturas/`) |
| Carga | **Medido** en entorno de desarrollo (`docs/evidencia/carga.md`) |
| `docker compose`, Vault real, MongoDB real | **NO ejecutado** en el entorno de desarrollo (sin Docker). El compose se validó solo sintácticamente; en las pruebas la base es `mongomock` y Vault es un servidor falso KV v2. Debe comprobarse con la lista de `docs/modulos/10-backend-integracion.md` |
| Proveedor de pagos | **Sandbox simulado** (el protocolo de firma sí es el real) |

## Arranque con Docker (despliegue reproducible)

```bash
cd "Unidad 2/evaluacion2"
python scripts/init_env.py                            # crea deploy/.env con secretos al azar (no se versiona)
docker compose -f deploy/docker-compose.yml up --build
# Front-end: http://localhost:8080      API: http://localhost:8000/api/v1
```

Solo se publican los puertos 8000 y 8080. Vault y MongoDB viven en la red interna. Los datos de MongoDB persisten en el volumen `mongo-data`.
Usuarios ficticios (contraseña = `LR_SEED_PASSWORD` de `deploy/.env`): `ana@ejemplo.cl`, `beto@ejemplo.cl` (clientes), `tienda@libreyrico.test` (personal), `admin@libreyrico.test`, `auditoria@libreyrico.test`.

## Arranque local sin Docker (desarrollo y pruebas)

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python scripts/dev_local.py        # 7 procesos, base en memoria, secretos por variables de entorno; imprime la contraseña de prueba
php -S localhost:8080 -t frontend  # en otra terminal (o cualquier servidor PHP)
```

## Pruebas y evidencia

```bash
pytest tests                              # 37 pruebas e2e + resiliencia + cliente de Vault
python scripts/generar_docs.py --pruebas  # reejecuta pytest, regenera matrices e INFORME.md
python scripts/carga.py --segundos 12 --concurrencia 25   # escribe docs/evidencia/carga.md
python scripts/ejemplos_graphql.py        # ejemplos reales de GraphQL
python tests/browser_e2e.py               # requiere Playwright; capturas y resultados-navegador.json
```

## Estructura

| Ruta | Contenido |
|---|---|
| `backend/<servicio>/main.py` | cada servicio; `backend/common/lr_common` = secretos, logs, base, cliente HTTP, errores |
| `backend/gateway/routes.py` | tabla de rutas S01–S26 (fuente de la matriz del informe) |
| `scripts/topology.py` | aristas de confianza y servicios con base (fuente de claves y políticas) |
| `deploy/` | `docker-compose.yml`, `.env.example` |
| `frontend/` | páginas PHP y `assets/js` (sin secretos; datos con `textContent`) |
| `docs/modulos/` | informe por módulo; `docs/INFORME.md` lo ensambla |
| `docs/diagramas/` | fuentes Mermaid (`.mmd`) y PNG |
| `docs/evidencia/` | resultados de pruebas, carga, GraphQL y capturas |

## Seguridad en una línea por capa

Gateway con tabla de rutas, límites, origen, sesión y rol · servicios privados con clave por arista y re-verificación de rol/propiedad · secretos en Vault con política de solo lectura por servicio · contraseñas Argon2id, sesiones opacas con hash · precios y «pagado» decididos solo por el servidor (webhook firmado) · GraphQL de solo lectura con límites de consulta.

## Límites conocidos

Limitador de solicitudes en memoria (una instancia de gateway) · sin TLS (usar proxy con HTTPS y `LR_COOKIE_SECURE=1`) · Vault en modo dev en el compose (no persiste ni se sella) · mediciones de carga en entorno de desarrollo · usuarios y datos ficticios.
