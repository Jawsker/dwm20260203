# Módulo 1 · Servicios y contratos

## Servicios y responsabilidades

| Servicio | Puerto | Responsabilidad | Base propia | Expuesto al navegador |
|---|---:|---|---|---|
| API Gateway | 8000 | Único punto de entrada: sesión, rol, origen, tamaño, límite, enrutamiento y traducción de errores | no | **sí** (también el webhook del proveedor) |
| Auth | 8001 | Cuentas, contraseñas (Argon2id), sesiones, bloqueo por intentos | `auth` | no |
| Clients | 8002 | Perfil del cliente y mensajes de contacto | `clients` | no |
| Inventory | 8003 | Catálogo, stock y reservas atómicas | `inventory` | no |
| Orders | 8004 | Pedidos, precios del servidor, estados, expiración, idempotencia | `orders` | no |
| Payments | 8005 | Intención de pago, sandbox, webhook firmado | `payments` | no |
| GraphQL | 8006 | Agregación de lectura sin base propia | no | no (solo vía gateway) |

## Matriz de servicios (26 operaciones externas)

Generada desde `backend/gateway/routes.py`, que es la tabla que el gateway ejecuta: lo documentado es lo implementado.

{{incluir:generado/m1-matriz-servicios.md}}

## Formato común de contratos

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
