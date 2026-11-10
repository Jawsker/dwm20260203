# Módulo 8 · Servicios privados y GraphQL

## Qué es privado y por qué

| Servicio | Accesible desde Internet | Por qué |
|---|---|---|
| gateway | **sí** (puerto 8000) | único punto de entrada |
| auth, clients, inventory, orders, payments, graphql | no | solo alcanzables desde la red interna con clave de arista |
| mongo, vault | no | solo desde servicios con credenciales propias |

En `deploy/docker-compose.yml` solo se publican `8000` y `8080` (front-end). La red `private` es `internal: true`.

## Mapa de clasificación de servicios

| Servicio | Naturaleza | Responsabilidad | Datos propios | Contrato | Dependencias | Justificación de la separación |
|---|---|---|---|---|---|---|
| gateway | borde (público) | controles de entrada y enrutamiento | ninguno | REST externo `/api/v1` | auth, todos | una sola puerta que se endurece una vez |
| auth | transaccional, privado | identidad y sesiones | usuarios, sesiones | REST interno | — | las credenciales se aíslan del resto de los datos |
| clients | transaccional, privado | datos personales y contacto | perfiles, mensajes | REST interno | — | datos personales con su propia base y rol de acceso |
| inventory | transaccional, privado | catálogo y stock | productos, reservas | REST interno | — | el stock necesita operaciones atómicas propias |
| orders | transaccional, privado | pedidos y estados | pedidos | REST interno | inventory, payments | es la autoridad del estado del pedido |
| payments | transaccional, privado | pagos y eventos del proveedor | pagos, eventos | REST interno + webhook | orders | aísla la integración con el proveedor y su secreto |
| graphql | **agregación**, privado | lectura combinada | ninguno | GraphQL interno | orders, inventory, clients | evita que el front-end haga varias llamadas y no toca bases ajenas |
| vault, mongo | infraestructura | secretos y persistencia | secretos / datos | — | — | inaccesibles desde Internet |

**Analítica y alta demanda:** no hay servicio de analítica ni de alta demanda separado (decisión en el Módulo 9).

**Cohesión y acoplamiento:** cada servicio modifica solo sus datos; las colaboraciones son por contratos REST explícitos (aristas de `topology.py`). La agregación **no accede a bases de otros servicios**: solo llama a sus APIs.

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
