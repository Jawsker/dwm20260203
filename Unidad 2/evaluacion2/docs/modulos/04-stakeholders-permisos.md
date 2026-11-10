# Módulo 4 · Actores y matriz de permisos

## Actores

| Actor | Rol técnico | Qué necesita | Qué NO debe poder hacer |
|---|---|---|---|
| Visitante | anónimo | ver catálogo, crear cuenta, escribir al contacto | ver pedidos, perfiles, stock exacto |
| Cliente | `customer` | comprar, pagar, ver/cancelar **sus** pedidos, gestionar **su** perfil | ver pedidos o datos de otros, cambiar precios/estados, administrar |
| Personal de tienda | `staff` | ver pedidos, avanzar preparación, ajustar stock, leer contacto | crear productos o cuentas; ver la dirección del cliente |
| Administración | `admin` | todo lo del personal + productos + altas de personal | pagar por un cliente; ver credenciales |
| Auditoría | `auditor` | ver pedidos y panel (solo lectura) | ver datos personales; modificar nada |
| Proveedor de pagos | sistema externo | notificar resultados | cualquier cosa fuera del webhook firmado |
| Equipo de operación | persona con acceso a infraestructura | desplegar, rotar secretos | leer secretos de otros servicios (cada uno tiene política de solo lectura propia) |

## Matriz de permisos por ruta, verbo y condición

✔ permitido · 401 requiere sesión · 403 rol sin permiso. La columna final es la condición **dentro** del servicio dueño (el gateway no la puede verificar sola).

{{incluir:generado/m4-permisos.md}}

**Defensa en profundidad:** el gateway filtra por rol (primera capa) y el servicio dueño **vuelve a verificar** rol y propiedad con la identidad que le llega firmada por clave de arista (segunda capa). Un servicio privado rechaza llamadas sin clave de arista (401) y descarta cualquier `X-Auth-User/Role` que no venga del gateway o de graphql.

## Registro de stakeholders (partes interesadas)

| Stakeholder | Interés | Rol asociado | Uso de información |
|---|---|---|---|
| Visitante | conocer y comparar productos | anónimo | catálogo público |
| Cliente | comprar y seguir su pedido | `customer` | sus pedidos, su perfil |
| Personal de tienda | preparar y entregar pedidos | `staff` | pedidos, stock, mensajes de contacto |
| Administración | operar el negocio y el catálogo | `admin` | todo lo anterior + productos y cuentas |
| Auditoría | supervisar sin intervenir | `auditor` | pedidos y panel, sin datos personales |
| **Dueño/gerencia del negocio** | conocer ventas y estado operativo | **sin permisos operativos** | recibe la información a través del panel de operación de solo lectura (cuenta de auditoría) o de administración; no invoca servicios por sí mismo |
| **Contabilidad / tributario** | conciliar ventas pagadas | **sin permisos operativos** | recibe el total de ventas pagadas del panel (`ventasPagadas`); los pedidos pagados se conservan aunque la cuenta del cliente se elimine (anonimizados) |
| Proveedor de pagos | notificar resultados | identidad técnica (webhook firmado) | solo el evento de pago; no tiene sesión de usuario |
| Equipo de operación (TI) | desplegar y rotar secretos | identidad técnica de infraestructura | claves de Vault; no lee secretos de otros servicios por política |

## Dónde se verifica cada permiso

| Capa | Qué verifica | Ejemplo |
|---|---|---|
| API Gateway | autenticación (sesión) y **rol** por ruta | `GET /admin/contact` con cliente → 403 sin llegar al servicio |
| Servicio dueño | **rol otra vez** y **propiedad** del recurso | `GET /orders/{id}` de otro cliente → 404; auditoría sin identidad |
| Entre servicios | identidad del servicio llamador | clave de arista; cabeceras de identidad solo desde gateway/graphql |

La **identidad** (quién eres: sesión o clave de servicio) se separa de la **autorización** (qué puedes hacer: rol y propiedad). Ocultar un botón en el front-end no otorga ni quita permisos: la prueba `test_V3_*` ejecuta las operaciones de administración con roles sin permiso y recibe 403.

## Criterios técnicos aplicados (verbos)

* **GET** solo consulta; **POST** crea recursos o ejecuta acciones justificadas (cancelar, pagar, cambiar estado); **PUT** modifica un recurso ya existente (aquí actualiza los campos enviados, no reemplaza el documento completo; se documenta esa semántica y no se usa PATCH); **DELETE** solo en `/account` (el titular elimina sus datos).
* **Anular un pedido no lo borra:** `POST /orders/{id}/cancel` cambia el estado a `cancelled`, libera el stock y conserva el registro y su `historial` de estados. No existe DELETE de pedidos ni de productos (un producto se desactiva con `activo=false`).
* Una ruta con un verbo permitido **no** autoriza todas las rutas: cada ruta tiene su propia fila en la matriz.
