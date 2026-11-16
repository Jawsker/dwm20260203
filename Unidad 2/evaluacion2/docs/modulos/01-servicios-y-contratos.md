# Módulo 1 · Servicios y contratos

## Servicios y responsabilidades

| Servicio | Carpeta | Puerto | Responsabilidad | Base propia | Expuesto al navegador |
|---|---|---:|---|---|---|
| API Gateway | `apigateway/gateway/gateway.py` | 8000 | Único punto de entrada: sesión, rol, origen, tamaño, límite, enrutamiento y traducción de errores | no | **sí** (también el webhook del proveedor) |
| Auth Service | `apigateway/auth-service/auth_service.py` | 8100 | Cuentas, contraseñas (Argon2id), sesiones, bloqueo por intentos | `auth` | no |
| Inventory | `apigateway/inventory/backend_api.py` | 9000 | Catálogo, stock y reservas atómicas | `inventory` | no |
| Orders | `apigateway/orders/backend_api.py` | 9100 | Pedidos, precios del servidor, estados, expiración, idempotencia; publica eventos STOMP | `orders` | no |
| Clients | `apigateway/clients/backend_api.py` | 9200 | Perfil del cliente y mensajes de contacto | `clients` | no |
| Payments | `apigateway/payments/backend_api.py` | 9300 | Intención de pago, sandbox, webhook firmado | `payments` | no |
| GraphQL Gateway | `graphql/server.py` | 8090 | Agregación de lectura sin base propia | no | no (solo vía gateway) |
| Mensajería | `stomp/productor.py`, `stomp/consumidor.py` | 61613 (broker) | Aviso «pedido pagado» en la cola `/queue/pedidos` | no | no |
| Vault / MongoDB | infraestructura | 8200 / 27017 | Secretos / persistencia | — | no |

La distribución de carpetas y puertos sigue la del material del curso (`apigateway/gateway`, `apigateway/auth-service`, backends en 9000+, GraphQL en 8090, Vault en 8200, STOMP en 61613). Los puertos están definidos una sola vez en `apigateway/common/lr_common/ports.py`.

## Matriz de servicios (27 operaciones externas)

Generada desde `apigateway/gateway/routes.py`, que es la tabla que el gateway ejecuta: lo documentado es lo implementado.

{{incluir:generado/m1-matriz-servicios.md}}

## Formato común de contratos

* **Autenticación:** el sitio usa una cookie de sesión `HttpOnly` (S04). Para clientes que no son navegador (curl, Postman) existe S27 `POST /auth/token`, que entrega el mismo token como `Bearer` y **no** crea cookie; el gateway acepta `Authorization: Bearer <token>` con exactamente los mismos controles de sesión y rol.

* JSON (UTF-8); fechas ISO-8601 en UTC con `Z`; dinero en **pesos chilenos enteros** (sin decimales).
* Todo error tiene la misma forma: `{"error": {"code": "...", "message": "...", "correlation_id": "...", "details": [...]}}`. Los mensajes no revelan detalles internos ni distinguen «correo inexistente» de «clave errónea».
* Cada respuesta lleva `X-Correlation-Id`, que aparece en los registros de todos los servicios implicados.

## Ejemplos de contratos (S12 crear pedido, S14 pagar, S20 GraphQL)

**S12 · `POST /api/v1/orders`** — cabecera opcional `Idempotency-Key`

```json
{ "items": [ {"product_id": "p01", "qty": 2}, {"product_id": "p03", "qty": 1} ], "notes": "retiro tarde" }
```

Respuesta `201` (precios y total los calcula el servidor; el cliente no envía ninguno):

```json
{ "id": "LR-F1E40D4B", "status": "awaiting_payment", "total": 9370, "currency": "CLP",
  "expires_at": "2026-11-09T18:30:00Z",
  "items": [ {"product_id":"p01","nombre":"Pan de molde","qty":2,"unit_price":3190,"subtotal":6380},
             {"product_id":"p03","nombre":"Hallulla sin gluten","qty":1,"unit_price":2990,"subtotal":2990} ] }
```

Errores: `400 duplicate_items | validation_error` · `401` · `403` (rol no cliente) · `409 insufficient_stock | product_unavailable` · `429 rate_limited` · `503 upstream_unavailable`.

**S14 · `POST /api/v1/orders/{id}/pay`** (sin cuerpo) → `200 {"order_id","payment_id","provider_ref","amount"}`; el monto sale del pedido guardado, nunca de la solicitud.

**S19 · `POST /api/v1/webhooks/payments`** (lo llama el proveedor) — cabecera `X-Provider-Signature: t=<epoch>,v1=<hmac-sha256(secreto, "<t>." + cuerpo)>`; cuerpo `{"event_id","type","provider_ref","amount"}`. Respuestas: `200 processed|duplicate|ignored`, `401 invalid_signature`, `400 amount_mismatch`.

**S20 · `POST /api/v1/graphql`** — ver Módulo 8, con ejemplos reales de consulta y respuesta.

## Ejemplo JSON de cada contrato (S01–S27)

Cada operación se ejecutó contra el sistema con **datos ficticios**; abajo están las solicitudes y respuestas reales (cookies y firmas redactadas). Incluyen casos de error representativos (filtro inválido, credenciales inválidas, pedido ajeno, firma falsa). Se regeneran con `python scripts/ejemplos_contratos.py`.

**Qué envía el navegador y qué decide el servidor:** el navegador envía solo ids y cantidades (S12), credenciales (S03/S04) y campos de perfil (S08). El servidor calcula precios, total y estados, fija el rol, fija el dueño del recurso (sale de la sesión, nunca de un parámetro) y decide si un pago está confirmado. Los precios, totales y estados de pago que un cliente intente enviar se ignoran (prueba `test_V6_*`).

{{incluir:evidencia/ejemplos-contratos.md}}
