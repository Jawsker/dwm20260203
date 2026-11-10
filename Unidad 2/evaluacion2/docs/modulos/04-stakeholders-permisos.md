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
