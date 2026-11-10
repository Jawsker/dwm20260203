# Módulo 3 · Matriz de sistemas, mapa de componentes y secuencia

## Matriz de sistemas

| Sistema | Tipo | Quién lo llama | A quién llama | Protocolo | Credencial |
|---|---|---|---|---|---|
| Navegador | cliente externo | — | Gateway | HTTP/JSON + cookie `HttpOnly` | sesión del usuario |
| Proveedor de pagos (sandbox) | externo | — | Gateway (webhook) | HTTP + firma HMAC | `payments/webhook` |
| API Gateway | borde propio | navegador, proveedor | auth, clients, inventory, orders, payments, graphql | HTTP/JSON | `edge/gateway__*` |
| Auth | interno | gateway | — | HTTP/JSON | `edge/gateway__auth` |
| Clients | interno | gateway, graphql | — | HTTP/JSON | `edge/gateway__clients`, `edge/graphql__clients` |
| Inventory | interno | gateway, orders, graphql | — | HTTP/JSON | `edge/gateway__inventory`, `edge/orders__inventory`, `edge/graphql__inventory` |
| Orders | interno | gateway, payments, graphql | inventory, payments | HTTP/JSON | `edge/gateway__orders`, `edge/payments__orders`, `edge/graphql__orders` |
| Payments | interno | gateway, orders | orders | HTTP/JSON | `edge/gateway__payments`, `edge/orders__payments` |
| GraphQL | interno | gateway | orders, inventory, clients | HTTP/JSON (lectura) | `edge/gateway__graphql` |
| Vault | infraestructura | todos los servicios | — | HTTPS/JSON | token propio por servicio |
| MongoDB | infraestructura | los 5 servicios con datos | — | MongoDB wire (`mongodb://…`) | usuario propio por servicio |

La lista de aristas sale de `scripts/topology.py` (única fuente de verdad): de ella se generan el inventario de secretos, las políticas de Vault y las claves del arranque.

## Mapa de componentes

![Mapa de componentes](../diagramas/componentes.png)

## Secuencia: compra, pago y confirmación

![Secuencia de compra](../diagramas/secuencia_compra.png)

Puntos de diseño visibles en la secuencia: (1) el navegador nunca envía precio ni estado; (2) `orders` obtiene los precios de `inventory` en el momento; (3) el monto del pago sale del pedido guardado; (4) el «pagado» llega por un evento firmado, verificado dos veces (firma/monto/duplicado en `payments`; monto otra vez en `orders`); (5) `commit` de la reserva descuenta el stock físico solo al confirmar.
