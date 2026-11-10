| ID | Verbo y ruta | Anónimo | Cliente | Personal | Admin. | Auditoría | Condición adicional (propiedad / campo) |
|---|---|---|---|---|---|---|---|
| S01 | `GET /api/v1/products` | ✔ | ✔ | ✔ | ✔ | ✔ | — |
| S02 | `GET /api/v1/products/{product_id}` | ✔ | ✔ | ✔ | ✔ | ✔ | — |
| S03 | `POST /api/v1/auth/register` | ✔ | ✔ | ✔ | ✔ | ✔ | El rol lo fija el servidor (customer) |
| S04 | `POST /api/v1/auth/login` | ✔ | ✔ | ✔ | ✔ | ✔ | — |
| S05 | `POST /api/v1/auth/logout` | 401 | ✔ | ✔ | ✔ | ✔ | Solo su propia sesión |
| S06 | `GET /api/v1/auth/session` | 401 | ✔ | ✔ | ✔ | ✔ | Solo la propia |
| S07 | `GET /api/v1/clients/me` | 401 | ✔ | 403 | 403 | 403 | id = sesión |
| S08 | `PUT /api/v1/clients/me` | 401 | ✔ | 403 | 403 | 403 | id = sesión |
| S09 | `DELETE /api/v1/account` | 401 | ✔ | 403 | 403 | 403 | Solo la propia cuenta |
| S10 | `POST /api/v1/contact` | ✔ | ✔ | ✔ | ✔ | ✔ | — |
| S11 | `GET /api/v1/admin/contact` | 401 | 403 | ✔ | ✔ | 403 | Solo personal/administración |
| S12 | `POST /api/v1/orders` | 401 | ✔ | 403 | 403 | 403 | customer: pedido a nombre de la sesión |
| S13 | `GET /api/v1/orders/{order_id}` | 401 | ✔ | ✔ | ✔ | ✔ | Dueño; personal/admin/auditoría ven todos (auditoría sin identidad) |
| S14 | `POST /api/v1/orders/{order_id}/pay` | 401 | ✔ | 403 | 403 | 403 | Dueño del pedido |
| S15 | `POST /api/v1/orders/{order_id}/cancel` | 401 | ✔ | ✔ | ✔ | 403 | Dueño; personal/admin |
| S16 | `POST /api/v1/admin/orders/{order_id}/status` | 401 | 403 | ✔ | ✔ | 403 | Personal/administración |
| S17 | `GET /api/v1/payments/{provider_ref}` | 401 | ✔ | 403 | 403 | 403 | Dueño del pago |
| S18 | `POST /api/v1/payments/{provider_ref}/sandbox-decision` | 401 | ✔ | 403 | 403 | 403 | Dueño del pago |
| S19 | `POST /api/v1/webhooks/payments` | ✔ | ✔ | ✔ | ✔ | ✔ | Autenticada por firma, no por usuario |
| S20 | `POST /api/v1/graphql` | 401 | ✔ | ✔ | ✔ | ✔ | Por recurso y campo en cada servicio |
| S21 | `GET /api/v1/admin/products` | 401 | 403 | ✔ | ✔ | 403 | Personal/administración |
| S22 | `POST /api/v1/admin/products` | 401 | 403 | 403 | ✔ | 403 | Solo administración |
| S23 | `PUT /api/v1/admin/products/{product_id}` | 401 | 403 | 403 | ✔ | 403 | Solo administración |
| S24 | `PUT /api/v1/admin/products/{product_id}/stock` | 401 | 403 | ✔ | ✔ | 403 | Personal/administración |
| S25 | `POST /api/v1/admin/users` | 401 | 403 | 403 | ✔ | 403 | Solo administración |
| S26 | `POST /api/v1/admin/maintenance/sweep` | 401 | 403 | 403 | ✔ | 403 | Solo administración |
