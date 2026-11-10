# Módulo 7 · Datos sensibles, secretos de cliente y validaciones

## Matriz de datos y credenciales

| Dato o credencial | Finalidad | Clasificación | Sistema custodio | Roles autorizados | Representación en el front-end | Protección | Retención |
|---|---|---|---|---|---|---|---|
| Contraseña | autenticar | **Credencial** | Auth (solo hash Argon2id con sal) | nadie la lee | campo `password`, se vacía tras enviar; nunca se muestra | hash adaptativo, comparación de tiempo constante, no se devuelve ni se registra | mientras exista la cuenta; se borra al eliminarla |
| Token de sesión | mantener la sesión | **Credencial** | Auth (SHA-256 del token) | el propio navegador (cookie `HttpOnly`, ilegible por JS) | no existe en JS ni en `localStorage` | inactividad 30 min, absoluta 8 h, revocable al cerrar sesión o eliminar cuenta | hasta expirar o revocar |
| Correo | identificar y contactar | **Dato personal** | Auth | titular; personal/admin/auditoría solo lo ven como identidad en sesión propia | solo en el menú de cuenta del titular | HTTPS (proxy), no en logs | mientras exista la cuenta |
| Nombre, teléfono | coordinar retiro | **Dato personal restringido** | Clients | titular; personal (nombre y teléfono); admin | perfil propio; panel de operación para personal | mínimo por rol; fuera de logs | hasta que el titular elimine su cuenta |
| Dirección | datos de contacto del cliente | **Dato personal restringido** | Clients | titular; admin (no personal ni auditoría) | solo en «Mi perfil» y en el panel de admin | mínimo por rol; fuera de logs | hasta que el titular elimine su cuenta |
| Pedidos y montos | compra y seguimiento | **Dato comercial del cliente** | Orders | dueño; personal/admin; auditoría sin identidad | «Mis pedidos» (propios), panel de operación | 404 ante pedido ajeno; anonimización al eliminar cuenta | se **conservan** anonimizados (fines contables) |
| Pagos y referencia del proveedor | cobro | **Dato comercial** | Payments | dueño del pago | referencia mostrada solo en la pantalla de pago | monto verificado en servidor; firma de eventos | se conservan con el pedido |
| Mensaje de contacto | atender consultas | **Dato personal** | Clients | personal/admin | formulario (solo envío) | límite de frecuencia y de tamaño | **sin purga automática implementada** (brecha declarada: debería definirse un plazo) |
| Catálogo y precios | vender | **Público** | Inventory | todos | catálogo | solo campos permitidos | permanente |
| Stock exacto y reservas | operación | **Interno** | Inventory | personal/admin | panel de inventario | rol exigido en servidor | permanente |
| Claves de arista, de base de datos y de webhook | autenticar sistemas | **Secreto de integración** | Vault | cada servicio solo las suyas | **nunca** llegan al navegador | política de solo lectura por servicio; rotables | rotación (ver Módulo 6) |
| Registros (logs) | operación y diagnóstico | **Operacional** | cada servicio (salida estándar) | operación | — | JSON con redacción de claves sensibles; sin cuerpos de solicitud ni credenciales (`test_los_logs_*`) | la define la plataforma de despliegue |

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


**Control antes de entregar:** se buscó que no haya secretos en JavaScript, HTML, capturas ni ejemplos (búsqueda de claves y contraseñas en el repositorio y en `docs/`); los ejemplos usan datos ficticios y las contraseñas de prueba se generan en `deploy/.env`, que no se versiona. Se devuelven solo los campos mínimos por rol (ver Módulo 8).

**Token de pago / clave publicable:** el sandbox no usa token de tarjeta ni clave publicable en el navegador; con un proveedor real se debería usar su token de pago del lado del cliente (clasificación: identificador no secreto, alcance de un solo pago) y mantener la clave secreta solo en `payments`.
