# Ejemplos reales de contratos S01–S26 (Módulo 1)

Generado por `python scripts/ejemplos_contratos.py` ejecutando cada operación contra el stack local con **datos ficticios**. Ids, fechas y referencias son de esa ejecución; cookies y firmas se redactan.

## S01 · `GET /api/v1/products?available=true&limit=2`

Respuesta **200**:
```json
{
  "items": [
    {
      "id": "p01",
      "categoria": "panes",
      "emoji": "🍞",
      "nombre": "Pan de molde",
      "descripcion": "Ideal para sándwiches, en formato de 500 g.",
      "precio": 3190,
      "disponible": true
    },
    {
      "id": "p02",
      "categoria": "panes",
      "emoji": "🥖",
      "nombre": "Baguette rústica",
      "descripcion": "Corteza crocante, miga suave. Unidad de 250 g.",
      "precio": 3490,
      "disponible": true
    }
  ],
  "total": 12,
  "categorias": [
    "panes",
    "pasteleria",
    "galletas",
    "salados"
  ]
}
```

## S01 · `GET /api/v1/products?categoria=inexistente` — filtro inválido

Respuesta **400**:
```json
{
  "error": {
    "code": "invalid_filter",
    "message": "Categoría desconocida.",
    "correlation_id": "9c2710f0ea81436c"
  }
}
```

## S02 · `GET /api/v1/products/p01`

Respuesta **200**:
```json
{
  "id": "p01",
  "categoria": "panes",
  "emoji": "🍞",
  "nombre": "Pan de molde",
  "descripcion": "Ideal para sándwiches, en formato de 500 g.",
  "precio": 3190,
  "disponible": true
}
```

## S03 · `POST /api/v1/auth/register`

Solicitud:
```json
{
  "email": "cliente-b4de@ejemplo.cl",
  "password": "Clave-ficticia-123",
  "nombre": "Cliente Ficticio",
  "telefono": "+56 9 1234 5678"
}
```
Respuesta **201**:
```json
{
  "user": {
    "id": "u_24774c0819e0",
    "email": "cliente-b4de@ejemplo.cl",
    "role": "customer"
  }
}
```

## S04 · `POST /api/v1/auth/login` — credenciales inválidas

Solicitud:
```json
{
  "email": "ana@ejemplo.cl",
  "password": "incorrecta-123"
}
```
Respuesta **401**:
```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Correo o contraseña incorrectos.",
    "correlation_id": "89973e0a947a4850"
  }
}
```

## S05 · `POST /api/v1/auth/logout`

Respuesta **204**:
```json
null
```

## S06 · `GET /api/v1/auth/session`

Respuesta **200**:
```json
{
  "user_id": "u_24774c0819e0",
  "role": "customer",
  "email": "cliente-b4de@ejemplo.cl"
}
```

## S07 · `GET /api/v1/clients/me`

Respuesta **200**:
```json
{
  "id": "u_24774c0819e0",
  "nombre": "Cliente Ficticio",
  "telefono": "+56 9 1234 5678",
  "direccion": null
}
```

## S08 · `PUT /api/v1/clients/me`

Solicitud:
```json
{
  "direccion": "Calle Ficticia 123, Santiago"
}
```
Respuesta **200**:
```json
{
  "id": "u_24774c0819e0",
  "nombre": "Cliente Ficticio",
  "telefono": "+56 9 1234 5678",
  "direccion": "Calle Ficticia 123, Santiago"
}
```

## S09 · `DELETE /api/v1/account`

Respuesta **204**:
```json
null
```

## S10 · `POST /api/v1/contact`

Solicitud:
```json
{
  "nombre": "Visitante Ficticio",
  "correo": "visita@ejemplo.cl",
  "mensaje": "¿Tienen pan sin gluten por encargo?"
}
```
Respuesta **201**:
```json
{
  "id": "4dcb5a347875",
  "status": "nuevo"
}
```

## S11 · `GET /api/v1/admin/contact?limit=2`

Respuesta **200**:
```json
{
  "items": [
    {
      "id": "4dcb5a347875",
      "nombre": "Visitante Ficticio",
      "correo": "visita@ejemplo.cl",
      "mensaje": "¿Tienen pan sin gluten por encargo?",
      "status": "nuevo",
      "created_at": "2026-11-10T03:00:10Z"
    }
  ]
}
```

## S12 · `POST /api/v1/orders`

Cabeceras relevantes: `{"Idempotency-Key": "demo-0001"}`

Solicitud:
```json
{
  "items": [
    {
      "product_id": "p01",
      "qty": 2
    },
    {
      "product_id": "p03",
      "qty": 1
    }
  ],
  "notes": "retiro en la tarde"
}
```
Respuesta **201**:
```json
{
  "id": "LR-50E6A1E0",
  "status": "awaiting_payment",
  "total": 9370,
  "currency": "CLP",
  "created_at": "2026-11-10T03:00:10Z",
  "expires_at": "2026-11-10T03:15:10Z",
  "items": [
    {
      "product_id": "p01",
      "nombre": "Pan de molde",
      "qty": 2,
      "unit_price": 3190,
      "subtotal": 6380
    },
    {
      "product_id": "p03",
      "nombre": "Hallulla sin gluten",
      "qty": 1,
      "unit_price": 2990,
      "subtotal": 2990
    }
  ],
  "payment": {
    "status": "none"
  },
  "refund_required": false,
  "customer_id": "u_ana",
  "notes": "retiro en la tarde"
}
```

## S12 · `POST /api/v1/orders` — segundo pedido, para cancelar

Solicitud:
```json
{
  "items": [
    {
      "product_id": "p02",
      "qty": 1
    }
  ]
}
```
Respuesta **201**:
```json
{
  "id": "LR-19A5F149",
  "status": "awaiting_payment",
  "total": 3490,
  "currency": "CLP",
  "created_at": "2026-11-10T03:00:11Z",
  "expires_at": "2026-11-10T03:15:11Z",
  "items": [
    {
      "product_id": "p02",
      "nombre": "Baguette rústica",
      "qty": 1,
      "unit_price": 3490,
      "subtotal": 3490
    }
  ],
  "payment": {
    "status": "none"
  },
  "refund_required": false,
  "customer_id": "u_ana",
  "notes": null
}
```

## S13 · `GET /api/v1/orders/LR-50E6A1E0`

Respuesta **200**:
```json
{
  "id": "LR-50E6A1E0",
  "status": "awaiting_payment",
  "total": 9370,
  "currency": "CLP",
  "created_at": "2026-11-10T03:00:10Z",
  "expires_at": "2026-11-10T03:15:10Z",
  "items": [
    {
      "product_id": "p01",
      "nombre": "Pan de molde",
      "qty": 2,
      "unit_price": 3190,
      "subtotal": 6380
    },
    {
      "product_id": "p03",
      "nombre": "Hallulla sin gluten",
      "qty": 1,
      "unit_price": 2990,
      "subtotal": 2990
    }
  ],
  "payment": {
    "status": "none"
  },
  "refund_required": false,
  "customer_id": "u_ana",
  "notes": "retiro en la tarde"
}
```

## S13 · `GET /api/v1/orders/LR-50E6A1E0` — otro cliente → no ve datos

Respuesta **404**:
```json
{
  "error": {
    "code": "not_found",
    "message": "Pedido no encontrado.",
    "correlation_id": "85d982c2c4164e56"
  }
}
```

## S14 · `POST /api/v1/orders/LR-50E6A1E0/pay`

Respuesta **200**:
```json
{
  "order_id": "LR-50E6A1E0",
  "payment_id": "pay_32c83965d844927f",
  "provider_ref": "sbx_n15zdgl0aAOdhbOCYDXnFg",
  "amount": 9370
}
```

## S15 · `POST /api/v1/orders/LR-19A5F149/cancel`

Respuesta **200**:
```json
{
  "id": "LR-19A5F149",
  "status": "cancelled",
  "total": 3490,
  "currency": "CLP",
  "created_at": "2026-11-10T03:00:11Z",
  "expires_at": "2026-11-10T03:15:11Z",
  "items": [
    {
      "product_id": "p02",
      "nombre": "Baguette rústica",
      "qty": 1,
      "unit_price": 3490,
      "subtotal": 3490
    }
  ],
  "payment": {
    "status": "none"
  },
  "refund_required": false,
  "customer_id": "u_ana",
  "notes": null
}
```

## S16 · `POST /api/v1/admin/orders/LR-50E6A1E0/status`

Solicitud:
```json
{
  "status": "preparing"
}
```
Respuesta **200**:
```json
{
  "id": "LR-50E6A1E0",
  "status": "preparing",
  "total": 9370,
  "currency": "CLP",
  "created_at": "2026-11-10T03:00:10Z",
  "expires_at": "2026-11-10T03:15:10Z",
  "items": [
    {
      "product_id": "p01",
      "nombre": "Pan de molde",
      "qty": 2,
      "unit_price": 3190,
      "subtotal": 6380
    },
    {
      "product_id": "p03",
      "nombre": "Hallulla sin gluten",
      "qty": 1,
      "unit_price": 2990,
      "subtotal": 2990
    }
  ],
  "payment": {
    "status": "succeeded"
  },
  "refund_required": false,
  "customer_id": "u_ana",
  "notes": "retiro en la tarde"
}
```

## S17 · `GET /api/v1/payments/sbx_n15zdgl0aAOdhbOCYDXnFg`

Respuesta **200**:
```json
{
  "payment_id": "pay_32c83965d844927f",
  "order_id": "LR-50E6A1E0",
  "amount": 9370,
  "currency": "CLP",
  "status": "pending"
}
```

## S18 · `POST /api/v1/payments/sbx_n15zdgl0aAOdhbOCYDXnFg/sandbox-decision`

Solicitud:
```json
{
  "outcome": "approve"
}
```
Respuesta **200**:
```json
{
  "event_id": "evt_50aa4ae980bed08e",
  "webhook_status": 200
}
```

## S19 · `POST /api/v1/webhooks/payments` — evento ya procesado por la decisión sandbox, firma válida

Cabeceras relevantes: `{"X-Provider-Signature": "t=<epoch>,v1=<hmac-sha256 redactado>"}`

Solicitud:
```json
{
  "event_id": "evt_demo_0f7efe",
  "type": "payment.succeeded",
  "provider_ref": "sbx_n15zdgl0aAOdhbOCYDXnFg",
  "amount": 9370
}
```
Respuesta **200**:
```json
{
  "duplicate_payment": true
}
```

## S19 · `POST /api/v1/webhooks/payments` — firma falsa

Cabeceras relevantes: `{"X-Provider-Signature": "t=<epoch>,v1=firma-falsa"}`

Solicitud:
```json
{
  "event_id": "evt_demo_0f7efe",
  "type": "payment.succeeded",
  "provider_ref": "sbx_n15zdgl0aAOdhbOCYDXnFg",
  "amount": 9370
}
```
Respuesta **401**:
```json
{
  "error": {
    "code": "invalid_signature",
    "message": "Firma del webhook inválida o vencida.",
    "correlation_id": "7e05d9a5f7b841e9"
  }
}
```

## S20 · `POST /api/v1/graphql`

Solicitud:
```json
{
  "query": "query { pedidos(primeros: 1) { total items { id estado total lineas { nombre cantidad } } } }"
}
```
Respuesta **200**:
```json
{
  "data": {
    "pedidos": {
      "total": 1,
      "items": [
        {
          "id": "LR-50E6A1E0",
          "estado": "preparing",
          "total": 9370,
          "lineas": [
            {
              "nombre": "Pan de molde",
              "cantidad": 2
            },
            {
              "nombre": "Hallulla sin gluten",
              "cantidad": 1
            }
          ]
        }
      ]
    }
  }
}
```

## S21 · `GET /api/v1/admin/products?limit=2`

Respuesta **200**:
```json
{
  "items": [
    {
      "id": "p01",
      "categoria": "panes",
      "emoji": "🍞",
      "nombre": "Pan de molde",
      "descripcion": "Ideal para sándwiches, en formato de 500 g.",
      "precio": 3190,
      "disponible": true,
      "stock": 18,
      "reservado": 0,
      "disponible_unidades": 18,
      "activo": true
    },
    {
      "id": "p02",
      "categoria": "panes",
      "emoji": "🥖",
      "nombre": "Baguette rústica",
      "descripcion": "Corteza crocante, miga suave. Unidad de 250 g.",
      "precio": 3490,
      "disponible": true,
      "stock": 20,
      "reservado": 0,
      "disponible_unidades": 20,
      "activo": true
    }
  ],
  "total": 12,
  "categorias": [
    "panes",
    "pasteleria",
    "galletas",
    "salados"
  ]
}
```

## S22 · `POST /api/v1/admin/products`

Solicitud:
```json
{
  "id": "pan-demo",
  "categoria": "panes",
  "emoji": "🍞",
  "nombre": "Pan demo",
  "descripcion": "Producto ficticio de ejemplo",
  "precio": 2500,
  "stock": 10
}
```
Respuesta **201**:
```json
{
  "id": "pan-demo",
  "categoria": "panes",
  "emoji": "🍞",
  "nombre": "Pan demo",
  "descripcion": "Producto ficticio de ejemplo",
  "precio": 2500,
  "disponible": true,
  "stock": 10,
  "reservado": 0,
  "disponible_unidades": 10,
  "activo": true
}
```

## S23 · `PUT /api/v1/admin/products/pan-demo`

Solicitud:
```json
{
  "precio": 2700
}
```
Respuesta **200**:
```json
{
  "id": "pan-demo",
  "categoria": "panes",
  "emoji": "🍞",
  "nombre": "Pan demo",
  "descripcion": "Producto ficticio de ejemplo",
  "precio": 2700,
  "disponible": true,
  "stock": 10,
  "reservado": 0,
  "disponible_unidades": 10,
  "activo": true
}
```

## S24 · `PUT /api/v1/admin/products/pan-demo/stock`

Solicitud:
```json
{
  "stock": 8
}
```
Respuesta **200**:
```json
{
  "id": "pan-demo",
  "categoria": "panes",
  "emoji": "🍞",
  "nombre": "Pan demo",
  "descripcion": "Producto ficticio de ejemplo",
  "precio": 2700,
  "disponible": true,
  "stock": 8,
  "reservado": 0,
  "disponible_unidades": 8,
  "activo": true
}
```

## S25 · `POST /api/v1/admin/users`

Solicitud:
```json
{
  "email": "personal-8e77@libreyrico.test",
  "password": "Clave-ficticia-123",
  "role": "staff"
}
```
Respuesta **201**:
```json
{
  "user_id": "u_55a856f082a7",
  "role": "staff"
}
```

## S26 · `POST /api/v1/admin/maintenance/sweep`

Respuesta **200**:
```json
{
  "expired": 0,
  "released_retried": 0,
  "commits_retried": 0
}
```
