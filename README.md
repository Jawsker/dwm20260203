# Libre & Rico — Sitio web (proyecto académico)

Sitio de una panadería ficticia especializada en productos sin gluten, desarrollado
como proyecto de curso para practicar **temas de Bootstrap**, **manejo de eventos con JavaScript**
y **personalización con CSS**.

## Integrante
- Matías Palma Santana

## Tecnologías utilizadas
- HTML5 + PHP (para reutilizar navbar y footer con `include`)
- [Bootstrap 5.3.8](https://getbootstrap.com/) (CDN)
- CSS3 (variables personalizadas, sin frameworks adicionales)
- JavaScript vanilla (sin librerías externas)
- Tipografías: [Fraunces](https://fonts.google.com/specimen/Fraunces) y [Work Sans](https://fonts.google.com/specimen/Work+Sans) (Google Fonts)

## Estructura del proyecto
```
site/
├── index.php              → Página de inicio (hero, carrusel de categorías, destacados)
├── empresa.php             → Quiénes somos, misión y equipo
├── servicios.php            → Servicios (pedidos, despacho, talleres, mayorista)
├── productos.php            → Catálogo con filtro por categoría
├── contacto.php              → Formulario de contacto con validación
├── includes/
│   ├── header.php            → Navbar, meta tags y modal de acceso (reutilizado en todas las páginas)
│   └── footer.php            → Pie de página y carga de scripts
└── assets/
    ├── css/custom.css        → Tema personalizado sobre Bootstrap
    └── js/custom.js          → Eventos personalizados
```

## Paleta de colores personalizada
Elegida en [Paletton](https://paletton.com/), esquema monocromático a partir del color
base `#AA5439`:

| Uso | Color |
|---|---|
| Fondo general | `#F7EEEB` |
| Fondo de secciones | `#E6CCC4` |
| Acento claro | `#CC9888` |
| Color base (botones, precios) | `#AA5439` |
| Hover de botones | `#88432E` |
| Etiquetas / eyebrows | `#4D2619` |
| Texto, navbar, footer | `#331911` |

## Temas de Bootstrap personalizados
- Sobrescritura de variables (`--bs-primary`, `--bs-body-font-family`, `--bs-body-bg`, etc.) para que los componentes de Bootstrap (botones, navbar, formularios) usen la paleta propia en vez de los colores por defecto.
- Componentes de Bootstrap utilizados: **Navbar** con dropdown, **Modal**, **Carousel**, **Cards**, **Forms**, **Collapse** (menú responsive).

## Eventos JavaScript implementados
Todos en `assets/js/custom.js`:
1. **Navbar dinámico**: cambia de tamaño y agrega sombra al hacer scroll.
2. **Botón "volver arriba"**: aparece después de cierto scroll y hace scroll suave al hacer clic.
3. **Filtro de productos**: en `productos.php`, los botones de categoría muestran/ocultan tarjetas de producto y actualizan un contador dinámico.
4. **Validación de formulario de contacto**: valida nombre, correo (regex), motivo y largo del mensaje sin recargar la página; muestra un toast de confirmación al enviar.
5. **Login simulado**: valida el formulario del modal de acceso y muestra un mensaje de éxito o error.

## CSS personalizado
- Variables propias (`--lr-*`) para toda la paleta.
- Componentes hechos a medida: tarjetas de producto (`.lr-card`), sello circular tipo timbre (`.lr-stamp`), divisor de "papel rasgado" (`.lr-torn`), carrusel de categorías (`.lr-carousel`).
- Diseño responsive (mobile-first en breakpoints de Bootstrap) y soporte de `prefers-reduced-motion` para accesibilidad.

## Cómo ejecutar el proyecto
1. Copiar la carpeta `Entrega v.1/` dentro del directorio de un servidor local con PHP (ej. `htdocs` de XAMPP).
2. Iniciar Apache.
3. Abrir `http://localhost/Entrega v.1/index.php` en el navegador.
