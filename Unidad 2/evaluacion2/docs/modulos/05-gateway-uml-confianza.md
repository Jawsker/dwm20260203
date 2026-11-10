# Módulo 5 · API Gateway: UML y fronteras de confianza

## Diseño del gateway

![Diagrama UML del gateway](../diagramas/gateway_uml.png)

Orden fijo de controles por solicitud (`backend/gateway/main.py`):

1. **Tabla de rutas explícita** (`routes.py`, S01–S26): lo que no está en la tabla responde 404/405; no existe «reenviar todo lo que empiece con /api».
2. **Límite de solicitudes** por clase de ruta e IP (login 20/min, contacto 5/min, escritura 60/min, públicas 240/min; configurables) → `429` con `retry_after`.
3. **Tamaño de cuerpo** máximo por ruta y `Content-Type: application/json` obligatorio → `413`/`415`.
4. **Origen (CSRF):** en métodos que modifican, `Origin`/`Referer` debe estar en la lista permitida; además la cookie es `SameSite=Lax`.
5. **Sesión:** la cookie `lr_session` se introspecciona en Auth en cada solicitud; el rol se lee **del usuario**, no de la sesión (un cambio de rol surte efecto de inmediato).
6. **Política de rol** por ruta → `401`/`403`.
7. **Reenvío mínimo:** solo cabeceras en lista blanca por ruta; se descartan `X-Auth-*` que traiga el cliente y se inyectan los verificados; se añade la clave de arista (`edge/gateway__<destino>`).
8. **Traducción de fallos:** `504` si el destino no responde a tiempo, `503` si no hay conexión, `502` si falla internamente; los 5xx controlados del destino (con `code`) se propagan sin exponer detalles.
9. **Cabeceras de seguridad** (`X-Content-Type-Options`, `Cache-Control: no-store`, etc.) y **CORS** con lista de orígenes explícita y `credentials`.

La cookie de sesión es `HttpOnly`, `SameSite=Lax`, `Path=/` y `Secure` cuando `LR_COOKIE_SECURE=1` (obligatorio tras TLS). El gateway **no almacena datos**: solo orquesta registro/ingreso/salida/eliminación de cuenta (Auth + Clients + Orders).

## Fronteras de confianza

![Fronteras de confianza](../diagramas/fronteras_confianza.png)

| Frontera | Qué cruza | Control en la frontera |
|---|---|---|
| Z0 → Z1 (Internet → gateway) | todas las solicitudes del navegador y el webhook | tabla de rutas, límites, origen, sesión, rol, validación de tamaño y tipo |
| Z1 → Z2 (gateway → servicios) | solicitud + identidad verificada | clave de arista por llamador→destino (`hmac.compare_digest`); el servicio **re-verifica** rol y propiedad; identidad aceptada solo de gateway/graphql |
| Z2 → Z2 (servicio → servicio) | orders↔inventory, orders↔payments, graphql→(orders, inventory, clients) | solo las aristas listadas en `topology.py`; el resto devuelve 401 |
| Z2 → Z3 (servicios → Vault/Mongo) | secretos y datos | token de Vault de solo lectura por servicio; usuario de Mongo `readWrite` solo sobre su base |
| Webhook (Z0 → Z1 → payments) | evento del proveedor | firma HMAC-SHA256, tolerancia ±300 s, `event_id` único, monto exacto |

**Sin ruta (líneas punteadas):** desde Z0 no hay camino a servicios privados, MongoDB ni Vault: en compose solo se publican los puertos 8000 (gateway) y 8080 (front-end); la red `private` es `internal: true`. La prueba `test_V5_acceso_directo_al_backend_sin_identidad` verifica que llamar directo a un servicio sin identidad/clave falla.

## ¿Cuántos gateways y por qué?

Se usan **dos piezas con roles distintos**, no varios gateways de borde:

1. **Un API Gateway externo** (el único accesible desde Internet), con **políticas por clase de ruta** en una sola tabla: pública, con sesión, administrativa y webhook. Un solo equipo y una sola superficie de exposición no justifican separar el borde en varios gateways (más puertos, más configuración y más superficie que asegurar); las diferencias se resuelven con políticas (rol, límite, tamaño) por ruta.
2. **Un GraphQL Gateway privado**, dentro de la red interna, solo alcanzable desde el API Gateway (ruta S20). Existe por una razón concreta: agregar datos de varios servicios con control de campos y límites propios de GraphQL, sin exponer esos servicios.

## Clasificación de rutas

| Clase | Ejemplos | Datos restringidos |
|---|---|---|
| Externa anónima | S01 S02 S03 S04 S10 S19 (webhook, autenticada por firma) | no (S03/S04/S10 reciben datos, no los devuelven a terceros) |
| Externa autenticada | S05–S09 S12–S15 S17 S18 S20 | sí, solo para el titular |
| Administrativa | S11 S16 S21–S26 | sí, según rol |
| Interna | todas las `/internal/*` de los servicios; no existen en el gateway | — |

Una ruta pública de red puede transportar datos restringidos para un usuario autorizado (por ejemplo S13 devuelve un pedido al dueño): «pública en red» no es «dato público».

## Recorrido de una solicitud autorizada y una denegada

**Autorizada — Ana crea un pedido (`POST /api/v1/orders`):** (1) el gateway busca la ruta S12 en la tabla; (2) aplica límite de frecuencia, tamaño y tipo JSON, y comprueba `Origin`; (3) pide a Auth que valide la cookie → `{user_id: u_ana, role: customer}`; (4) la política de rol permite `customer`; (5) descarta cabeceras de identidad del cliente, agrega la identidad verificada y la clave `edge/gateway__orders` obtenida de `SecretProvider`; (6) Orders re-verifica rol, pide precios a Inventory, reserva el stock y responde 201 con el total calculado.

**Denegada (a) — rol insuficiente:** un cliente llama `GET /api/v1/admin/contact`. En el paso 4 la política de rol de la ruta S11 permite solo `staff` y `admin` → **403** sin que la solicitud llegue al servicio.

**Denegada (b) — propiedad:** Beto llama `GET /api/v1/orders/{id de Ana}`. El gateway lo deja pasar (es un cliente con sesión), pero **Orders** comprueba que el pedido no es suyo y responde **404** sin datos (ejemplo real en el Módulo 1, S13).

**Denegada (c) — acceso directo:** una llamada directa al puerto de un servicio privado sin clave de arista recibe **401** (`test_V5_*`); además en el despliegue ese puerto no está publicado.

## Qué valida cada uno

| Componente | Valida |
|---|---|
| API Gateway | ruta/verbo existentes, límite, tamaño, tipo, origen, sesión, rol; **no** conserva datos |
| Cada servicio privado | clave de arista del llamador, identidad aceptada solo de gateway/graphql, rol y propiedad, validación de datos y reglas de negocio |
| GraphQL Gateway | profundidad, alias y tokens de la consulta; delega la autorización de cada campo al servicio dueño |

**Relaciones estructurales vs flujos de red:** en el UML las líneas continuas/rombos son relaciones estructurales (el gateway *tiene* una tabla de rutas, el esquema *se compone* de resolvers); las flechas punteadas son dependencias de comunicación (el gateway *llama* a Auth, los servicios *leen* secretos del `SecretProvider`). Las fronteras de red están en el segundo diagrama.

**Rutas y secretos:** `RouteDefinition` solo guarda la **referencia simbólica** de la credencial; el valor lo entrega `SecretProvider` (Vault) en el momento. Políticas de rol, límites y destinos están separados de los secretos.
