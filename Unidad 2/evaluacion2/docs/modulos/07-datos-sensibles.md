# Módulo 7 · Datos sensibles, secretos de cliente y validaciones

## Clasificación de datos

| Dato | Clasificación | Dueño | Dónde se guarda | Quién lo ve | Tratamiento |
|---|---|---|---|---|---|
| Contraseña | **Credencial** | Auth | solo hash Argon2id | nadie | nunca se devuelve ni se registra; comparación de tiempo constante |
| Token de sesión | **Credencial** | Auth | SHA-256 del token (el original solo viaja en cookie `HttpOnly`) | el propio navegador (sin acceso por JS) | inactividad 30 min, absoluta 8 h, revocable |
| Claves de arista, de BD, de webhook | **Secreto de sistema** | Vault | Vault KV v2 | cada servicio, solo las suyas | rotables; nunca en repositorio, imagen ni logs |
| Correo, nombre, teléfono, dirección | **Dato personal restringido** | Auth/Clients | bases propias | el titular; personal (nombre/teléfono); admin (+dirección); auditoría: nada | minimización por rol; eliminación a solicitud |
| Pedidos y pagos | **Dato comercial del cliente** | Orders/Payments | bases propias | dueño y personal/admin/auditoría | 404 ante pedido ajeno; anonimización al borrar cuenta |
| Mensajes de contacto | **Dato personal** | Clients | base propia | solo personal/admin | límite de frecuencia y tamaño |
| Catálogo y precios | **Público** | Inventory | base propia | todos | stock exacto solo para personal |
| Stock exacto y reservas | **Interno** | Inventory | base propia | personal/admin | — |
| Registros (logs) | **Operacional** | cada servicio | salida estándar | operación | JSON con redacción de claves sensibles y sin cuerpos de solicitud (`test_los_logs_no_contienen_*`) |

## Decisión: ¿se custodian secretos del cliente?

**No.** El sistema no guarda ni procesa **datos de tarjeta** (ni PAN, ni CVV): el cliente paga en la pantalla del proveedor y el backend solo recibe el resultado firmado y una referencia (`provider_ref`). La única credencial del cliente es su contraseña, que se guarda **solo como hash Argon2id** (con sal propia, parámetros por defecto de `argon2-cffi`) y nunca es recuperable. Se evita así el alcance de PCI-DSS sobre datos de tarjeta y no existe ningún «secreto del cliente» que cifrar para poder devolverlo. Si el negocio exigiera guardar tarjetas, debería hacerse con tokenización del proveedor, no en este sistema.

## Ciclo de vida de un dato restringido (dirección del cliente)

| Etapa | Qué ocurre |
|---|---|
| Captura | el cliente la escribe en «Mi perfil»; validada (5–160 caracteres) y enviada por HTTPS al gateway |
| Uso | `GET /clients/me` (solo el titular) o, para administración, vía GraphQL `cliente`; el personal no recibe el campo |
| Almacenamiento | solo en la base `clients` (usuario Mongo propio); ningún otro servicio la copia |
| Registro | no aparece en logs (redacción de campos) |
| Eliminación | `DELETE /account`: borra perfil y credenciales y anonimiza los pedidos |

## Resultados de validación

Las pruebas **V1–V6** son las validaciones pedidas para este módulo; el resto cubre el comportamiento restante. Tabla completa generada desde `junit.xml` (ejecutada con `python scripts/generar_docs.py --pruebas`):

{{incluir:evidencia/resultados-pruebas.md}}

Pruebas de navegador (Playwright contra el front-end real): ver `docs/evidencia/resultados-navegador.json` y las capturas en `docs/evidencia/capturas/`.
