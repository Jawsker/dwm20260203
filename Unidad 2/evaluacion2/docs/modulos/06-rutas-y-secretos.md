# Módulo 6 · Matriz de rutas, inventario de secretos y operaciones GraphQL

## Matriz de rutas (gateway → servicio)

Generada desde `routes.py`. «Referencia de credencial» es el nombre simbólico en Vault; **ningún valor aparece en el repositorio ni en este informe**.

{{incluir:generado/m6-rutas.md}}

## Inventario de secretos (referencias simbólicas)

Generado desde `scripts/topology.py`. Los valores los crea `vault_bootstrap.py` al azar (256 bits) y solo se guardan en Vault. En ejecución local sin Vault se entregan por variables de entorno `LR_SECRET__<REF>__<CAMPO>` creadas al vuelo y no persistidas.

{{incluir:generado/m6-secretos.md}}

**Comportamiento ante fallas del gestor de secretos** (`lr_common/secrets.py`, probado en `test_04_cliente_vault`): caché con TTL corto; si Vault no responde se usa el **último valor conocido hasta `LR_SECRET_STALE_MAX` segundos** y luego se **falla cerrado** (503 `secrets_unavailable`); nunca se cae a un valor por defecto.

## Operaciones GraphQL

Un único punto externo (`POST /api/v1/graphql`, S20) hacia el servicio `graphql`, que **no tiene base de datos** y llama a los servicios dueños con la identidad del usuario.

| Operación | Tipo | Quién | Fuentes | Autorización |
|---|---|---|---|---|
| `yo` | query | cualquier sesión | identidad + clients | el perfil solo para `customer` (el suyo) |
| `pedidos(primeros, desplazamiento, estado)` | query | cliente (los suyos), personal/admin/auditoría (todos) | orders (+ inventory por línea, + clients por campo `cliente`) | filtrado en `orders`; `cliente` solo staff/admin |
| `resumenPedido(id)` | query | dueño o personal | orders (+ inventory) | `orders` responde 404 si es ajeno |
| `panelOperacion` | query | staff, admin, auditor | orders (`$group`) + inventory (bajo stock) | rol en graphql y en cada servicio; `productosBajoStock` puede fallar parcialmente |
| mutaciones | — | — | **no existen**: toda escritura es REST con validación propia | — |
