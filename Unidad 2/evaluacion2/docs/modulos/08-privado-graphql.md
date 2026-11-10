# Módulo 8 · Servicios privados y GraphQL

## Qué es privado y por qué

| Servicio | Accesible desde Internet | Por qué |
|---|---|---|
| gateway | **sí** (puerto 8000) | único punto de entrada |
| auth, clients, inventory, orders, payments, graphql | no | solo alcanzables desde la red interna con clave de arista |
| mongo, vault | no | solo desde servicios con credenciales propias |

En `deploy/docker-compose.yml` solo se publican `8000` y `8080` (front-end). La red `private` es `internal: true`.

## Esquema GraphQL (resumen)

```graphql
type Query {
  yo: Yo!
  resumenPedido(id: ID!): Pedido!
  pedidos(primeros: Int = 10, desplazamiento: Int = 0, estado: String): PaginaPedidos!
  panelOperacion: PanelOperacion!
}
type Pedido { id estado total moneda creado expira estadoPago requiereReembolso notas clienteRef lineas: [LineaPedido!]! cliente: Cliente }
type LineaPedido { productoId nombre cantidad precioUnitario subtotal producto: Producto }   # producto = datos VIGENTES (inventory)
type Cliente { id nombre telefono direccion }                                                 # según rol
type PanelOperacion { pedidosPorEstado: [EstadoConteo!]! ventasPagadas: Int! productosBajoStock: [ProductoBajoStock!] }
```

**Resolvers y fuentes:** `pedidos`/`resumenPedido` → orders; `LineaPedido.producto` → inventory (DataLoader por lote: una llamada por consulta, no una por línea); `Pedido.cliente` → clients (DataLoader, `/clients/batch`); `panelOperacion` → orders (`$group` en la base) + inventory. El servicio **no tiene base propia**.

## Autorización por campo

| Campo | Cliente | Personal | Admin | Auditoría |
|---|---|---|---|---|
| `pedidos` / `resumenPedido` | solo los suyos | todos | todos | todos (sin identidad del cliente) |
| `Pedido.cliente` | error `forbidden` en ese campo | nombre y teléfono | + dirección | error `forbidden` |
| `panelOperacion.pedidosPorEstado/ventas` | `forbidden` | ✔ | ✔ | ✔ |
| `panelOperacion.productosBajoStock` | `forbidden` | ✔ | ✔ | error parcial (campo `null`) |

La regla vive en el servicio dueño; GraphQL **no decide por su cuenta**, solo propaga la identidad verificada. Los errores son **parciales**: el resto de la respuesta se entrega y el campo fallido sale `null` con `extensions.code`.

## Límites de consulta (defensa contra consultas abusivas)

Profundidad máx. 6, alias máx. 4, tokens máx. 600, introspección desactivada (`LR_GQL_INTROSPECTION=1` solo en desarrollo), `primeros` entre 1 y 50, errores inesperados enmascarados (los de validación y autorización conservan su mensaje). Probado en `test_limites_de_consulta` y `test_limite_de_profundidad_graphql`.

## Evidencia de agregación desde el front-end

* «Mis pedidos» (`pedidos.js`) y el panel (`admin.js`) hacen **una** llamada a `/graphql`; el navegador no consulta orders e inventory por separado. Verificado por la prueba de navegador «P04 Mis pedidos (GraphQL) lista el pedido pagado con productos» y la captura `capturas/05-mis-pedidos-1280.png`.
* Ejemplos **reales** de consulta y respuesta (incluido el error parcial por rol y el pedido ajeno → 404): `docs/evidencia/ejemplos-graphql.md`, generado con `python scripts/ejemplos_graphql.py`.

{{incluir:evidencia/ejemplos-graphql.md}}
