# Ejemplos reales de GraphQL (Módulo 8)

Generado por `python scripts/ejemplos_graphql.py` contra el stack local; los ids y montos son de esa ejecución.

## 1. Cliente (Ana) consulta sus pedidos: agrega orders + inventory; el campo `cliente` queda prohibido

```graphql
query {
  pedidos(primeros: 2) {
    total
    items { id estado total lineas { nombre cantidad subtotal producto { precio disponible } } cliente { nombre } }
  }
}
```
```json
{
  "data": {
    "pedidos": {
      "total": 1,
      "items": [
        {
          "id": "LR-F1E40D4B",
          "estado": "awaiting_payment",
          "total": 9370,
          "lineas": [
            {
              "nombre": "Pan de molde",
              "cantidad": 2,
              "subtotal": 6380,
              "producto": {
                "precio": 3190,
                "disponible": true
              }
            },
            {
              "nombre": "Hallulla sin gluten",
              "cantidad": 1,
              "subtotal": 2990,
              "producto": {
                "precio": 2990,
                "disponible": true
              }
            }
          ],
          "cliente": null
        }
      ]
    }
  },
  "errors": [
    {
      "message": "Tu rol no puede consultar datos del cliente.",
      "locations": [
        {
          "line": 4,
          "column": 96
        }
      ],
      "path": [
        "pedidos",
        "items",
        0,
        "cliente"
      ],
      "extensions": {
        "code": "forbidden",
        "status": 403
      }
    }
  ]
}
```

## 2. Personal consulta los mismos pedidos: ahora sí ve `cliente` (clients), sin dirección

```graphql
query {
  pedidos(primeros: 2) {
    total
    items { id estado total lineas { nombre cantidad subtotal producto { precio disponible } } cliente { nombre } }
  }
}
```
```json
{
  "data": {
    "pedidos": {
      "total": 1,
      "items": [
        {
          "id": "LR-F1E40D4B",
          "estado": "awaiting_payment",
          "total": 9370,
          "lineas": [
            {
              "nombre": "Pan de molde",
              "cantidad": 2,
              "subtotal": 6380,
              "producto": {
                "precio": 3190,
                "disponible": true
              }
            },
            {
              "nombre": "Hallulla sin gluten",
              "cantidad": 1,
              "subtotal": 2990,
              "producto": {
                "precio": 2990,
                "disponible": true
              }
            }
          ],
          "cliente": {
            "nombre": "Ana Pérez (ficticia)"
          }
        }
      ]
    }
  }
}
```

## 3. Otro cliente (Beto) pide el pedido de Ana por id

```graphql
query { resumenPedido(id: "LR-F1E40D4B") { id total } }
```
```json
{
  "data": null,
  "errors": [
    {
      "message": "Pedido no encontrado.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "resumenPedido"
      ],
      "extensions": {
        "code": "not_found",
        "status": 404
      }
    }
  ]
}
```

## 4. Auditoría pide el panel: pedidos y ventas sí; bajo stock → error parcial si el rol no lo permite

```graphql
query { panelOperacion { pedidosPorEstado { estado cantidad } ventasPagadas productosBajoStock { nombre unidadesDisponibles } } }
```
```json
{
  "data": {
    "panelOperacion": {
      "pedidosPorEstado": [
        {
          "estado": "awaiting_payment",
          "cantidad": 1
        }
      ],
      "ventasPagadas": 0,
      "productosBajoStock": null
    }
  },
  "errors": [
    {
      "message": "Tu rol no permite esta operación.",
      "locations": [
        {
          "line": 1,
          "column": 77
        }
      ],
      "path": [
        "panelOperacion",
        "productosBajoStock"
      ],
      "extensions": {
        "code": "forbidden",
        "status": 403
      }
    }
  ]
}
```

## 5. Personal pide el panel completo (orders + inventory)

```graphql
query { panelOperacion { pedidosPorEstado { estado cantidad } ventasPagadas productosBajoStock { nombre unidadesDisponibles } } }
```
```json
{
  "data": {
    "panelOperacion": {
      "pedidosPorEstado": [
        {
          "estado": "awaiting_payment",
          "cantidad": 1
        }
      ],
      "ventasPagadas": 0,
      "productosBajoStock": []
    }
  }
}
```
