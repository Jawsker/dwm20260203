# Libre & Rico — Evaluación 1: prototipo front-end responsivo y dinámico

Prototipo front-end de una panadería ficticia sin gluten. Se implementa **una porción funcional coherente del caso**: armar y confirmar un pedido en línea. No hay backend: la comunicación con servicios se **simula**.

## 1. Caso, actor, objetivo y flujo

| Elemento | Definición |
|---|---|
| **Caso** | Venta en línea de una panadería sin gluten (Libre & Rico). |
| **Actor principal** | Cliente (persona celíaca o familia) que compra para retirar en tienda. |
| **Objetivo de usuario** | Armar un pedido con productos sin gluten y confirmarlo sin llamar por teléfono. |
| **Flujo implementado** | Consultar catálogo → filtrar / buscar → agregar al pedido → ajustar cantidades → confirmar pedido. |
| **Vistas** | Una página (`productos.php`) con dos regiones: catálogo y pedido. |

### Requisitos abordados
- **RF1** Consultar el catálogo desde un servicio simulado.
- **RF2** Filtrar por categoría y buscar por texto.
- **RF3** Agregar, sumar, restar y quitar productos del pedido, con total actualizado.
- **RF4** Confirmar el pedido (acción simulada) y recibir un número de pedido.
- **RF5** Ver estados de **carga, éxito, error y vacío**, con forma de recuperarse.

### Concerns de front-end y decisiones
| Concern | Decisión |
|---|---|
| Compatibilidad | Bootstrap 5.3.8 (grid) + JS vanilla sin dependencias; `fetch` y `Intl` estándar. |
| Rendimiento | Una sola consulta al catálogo; el filtro y la búsqueda se resuelven en el cliente; las tarjetas se insertan con `DocumentFragment`. |
| Accesibilidad | Regiones `aria-live` para estados, `role="alert"` en errores, botones con `aria-label`, `aria-pressed` en filtros, foco visible, `prefers-reduced-motion`. |
| Resiliencia | Un error del servicio no destruye la pantalla: el catálogo ofrece **Reintentar** y, si falla la confirmación, **el pedido se conserva**. |
| **Tensión de diseño** | En móvil el pedido y el catálogo compiten por espacio. Se resolvió apilándolos y agregando un botón flotante «Ver pedido (n)» para no obligar a un scroll largo antes de confirmar. |

## 2. Diseño previo y coherencia con la implementación

- Evidencia: [`docs/wireframe-productos.svg`](docs/wireframe-productos.svg) (vista PNG: [`docs/wireframe-productos.png`](docs/wireframe-productos.png)) con tres variantes —escritorio, tablet y móvil— y anotaciones numeradas que explican el *por qué*.

| Decisión del diseño | Cómo se transformó en código |
|---|---|
| Pedido siempre visible junto al catálogo en escritorio | Grid: catálogo `col-lg-8 col-xl-9` + pedido `col-lg-4 col-xl-3`, con `position: sticky` desde `lg`. |
| Pedido debajo del catálogo en tablet/móvil | Las columnas `col-12` se apilan bajo `lg`; botón `.lr-fab` (`d-lg-none`) lleva al pedido. |
| 1 / 2 / 3 tarjetas por fila | `row-cols-1 row-cols-sm-2 row-cols-xl-3`. |
| Filtros que no empujan el catálogo en móvil | Bajo 576 px los filtros pasan a una línea con scroll horizontal. |
| Tarjeta: imagen, texto que crece, pie con precio + botón | `.lr-card` en Flexbox (columna) y `.lr-card-footer` en fila con `space-between`. |
| Estados cargando / éxito / error / vacío | Componentes `.lr-estado` y alertas de Bootstrap generados por JS. |

## 3. Grid, Box Model y Flexbox: qué hace cada uno

**Grid (estructura general)** — Bootstrap, 12 columnas, con proporción = ancho del elemento ÷ ancho del contenedor y columnas ≈ 12 × proporción:

| Breakpoint | Catálogo | Pedido | Tarjetas por fila |
|---|---|---|---|
| < 992 px | 12/12 (100 %) | 12/12, debajo | 1 (<576) · 2 (≥576) |
| ≥ 992 px (lg) | 8/12 (≈ 67 %) | 4/12 (≈ 33 %) | 2 |
| ≥ 1200 px (xl) | 9/12 (75 %) | 3/12 (25 %) | 3 |

**Box Model (espacio y límites)** — `box-sizing: border-box` explícito; escala de espaciado en `rem` (`--lr-space-1…5`); imágenes con `aspect-ratio` en vez de altura fija; `min-width: 0` y `overflow-wrap` para que el texto largo no desborde; `min-width: min(16rem, calc(100vw - 2.5rem))` en el toast; padding con `clamp()` en secciones. Sin anchos fijos en px en los componentes del flujo.

**Flexbox (organización interna)** — tarjeta (columna que empuja el pie), pie de tarjeta (precio + botón con `wrap`), barra de filtros/búsqueda, panel de pedido (fila de producto: nombre · cantidad · subtotal · quitar), controles de cantidad y total.

## 4. JavaScript DOM (`assets/js/productos.js`)

- **Selección:** `querySelector` / `querySelectorAll`.
- **Eventos:** `addEventListener` (`click` delegado en filtros, catálogo y pedido; `input` en el buscador; `change` en el panel de pruebas).
- **Creación y eliminación de nodos:** `createElement`, `createDocumentFragment`, `appendChild`, remoción de hijos; los datos se insertan con `textContent` (nunca como HTML).
- **Cambio de clases/atributos/estados:** `classList`, `disabled`, `aria-pressed`, `dataset`.
- **Sin recargar la página:** el catálogo, los filtros, el pedido y los mensajes se generan en tiempo de ejecución. El HTML solo contiene contenedores vacíos.

## 5. Servicios simulados

| Archivo | Rol |
|---|---|
| `api/productos.json` | Datos del catálogo (12 productos y 4 categorías), servidos por HTTP. |
| `assets/js/api-dummy.js` | Capa de "API": `listarProductos()` (**consulta**, `fetch` al JSON con latencia) y `confirmarPedido()` (**acción simulada** tipo POST, responde 201 con número de pedido y retiro; 422/500 si falla). |

**Panel de pruebas** (desplegable al final de la página) para provocar cada estado:
`Normal` · `Catálogo lento` · `Catálogo con error` · `Catálogo vacío` · `Confirmación de pedido con error`.

## 6. Cómo ejecutar

Requiere un servidor HTTP (no funciona abriendo el archivo con `file://`, porque el catálogo se pide con `fetch`).

```bash
cd "Test/Entrega v.1"
php -S localhost:8000
```
Abrir `http://localhost:8000/productos.php`. (Con XAMPP: copiar la carpeta a `htdocs` y abrir `http://localhost/Entrega v.1/productos.php`.)

**Cómo probar el flujo:** agregar productos → ajustar cantidades → *Confirmar pedido* (verás carga y luego éxito). En *Panel de pruebas* elegir «Confirmación de pedido con error» y volver a confirmar: aparece el error y el pedido se conserva; volver a «Normal» y reintentar.

## 7. Evidencia de prueba responsiva (4 anchos de viewport)

Capturas de página completa en [`docs/pruebas-responsivas/`](docs/pruebas-responsivas/). Resultado medido en Chrome (headless): sin desborde horizontal en ningún ancho.

| Ancho | Dispositivo | Navbar | Tarjetas por fila | Pedido | Qué escala / refluye / se transforma |
|---|---|---|---|---|---|
| **360 px** | móvil | colapsada (hamburguesa) | 1 | debajo + botón flotante | Filtros pasan a una línea con scroll; buscador ocupa todo el ancho; el pedido se transforma en bloque apilado con acceso flotante. |
| **768 px** | tablet | colapsada | 2 | debajo + botón flotante | Las tarjetas reflowan a 2 columnas; los filtros se muestran completos y el buscador baja a una segunda fila. |
| **1024 px** | escritorio pequeño | expandida | 2 | **a la derecha (sticky)** | Cambia la macroestructura: el pedido sube a una columna lateral 4/12 que acompaña el scroll. |
| **1440 px** | escritorio | expandida | 3 | a la derecha (sticky) | Más espacio: el catálogo pasa a 9/12 con 3 columnas; el pedido a 3/12. |

Capturas de estados (1024 px): [`estado-carga`](docs/pruebas-responsivas/estado-carga-1024.png), [`estado-vacio`](docs/pruebas-responsivas/estado-vacio-1024.png), [`estado-error-catalogo`](docs/pruebas-responsivas/estado-error-catalogo-1024.png), [`estado-pedido-exito`](docs/pruebas-responsivas/estado-pedido-exito-1024.png), [`estado-pedido-error`](docs/pruebas-responsivas/estado-pedido-error-1024.png).

Además se ejecutó una prueba automatizada del flujo en 1024 y 360 px (46 comprobaciones: carga, filtro, búsqueda, estado vacío, sumar/restar/quitar, total, confirmación con éxito, error con pedido conservado, reintento y recuperación del catálogo) sin errores de consola.

> Nota: las capturas se tomaron sin acceso a Google Fonts, por lo que la tipografía se ve con la fuente de respaldo (Georgia / sans-serif del sistema).

## 8. Estructura del proyecto

```
Test/Entrega v.1/
├── productos.php            → Catálogo y pedido (flujo evaluado)
├── index.php · empresa.php · servicios.php · contacto.php
├── includes/header.php · footer.php
├── api/productos.json       → Datos del servicio simulado
├── assets/
│   ├── css/custom.css       → Tema, componentes, grid/box/flex, breakpoints
│   └── js/
│       ├── api-dummy.js     → API simulada (consulta + acción)
│       ├── productos.js     → DOM: catálogo, filtros, pedido, estados
│       └── custom.js        → Navbar, "volver arriba", formularios
└── docs/
    ├── wireframe-productos.svg / .png
    └── pruebas-responsivas/*.png
```

## 9. Lista de comprobación

- [x] Caso, actor y flujo claramente indicados
- [x] Evidencia de diseño previo con anotaciones (escritorio, tablet, móvil)
- [x] Grid system verificable (cambios reales por breakpoint)
- [x] Box Model aplicado de forma consciente
- [x] Flexbox para organización interna de componentes
- [x] Probado en cuatro anchos de viewport
- [x] JavaScript modifica el DOM durante la ejecución
- [x] Datos principales desde una respuesta simulada (no solo HTML estático)
- [x] Una consulta y una acción/modificación simulada
- [x] Estados de carga, éxito, error y vacío
- [x] Flujo completable sin backend real
- [x] README con ejecución y pruebas
