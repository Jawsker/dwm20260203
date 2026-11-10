# Evaluación 2 · Diseño e implementación de un backend seguro completo

**Caso:** Libre & Rico (panadería/pastelería sin gluten, venta web con retiro en tienda) · **Unidad 2** · Desarrollo Web y Móvil

**Equipo (integrante único):** Matías Palma Santana · **Fecha:** 09-11-2026

**Versión del front-end integrada:** sitio PHP + Bootstrap + JavaScript del repositorio `dwm20260203` (commit base `f481908`), extendido en esta entrega con `assets/js/{api,cuenta,productos,pago,pedidos,admin}.js` y las pantallas `productos.php`, `pago.php`, `mis-pedidos.php`, `admin.php`, `contacto.php`. El archivo `api-dummy.js` (datos simulados) fue **eliminado**: todas las pantallas consumen el backend real.

## Qué se entrega

| Pieza | Dónde |
|---|---|
| Código de 7 servicios (gateway, auth, clients, inventory, orders, payments, graphql) | `backend/` |
| Front-end integrado | `frontend/` |
| Despliegue reproducible (docker compose + Vault + MongoDB) | `deploy/`, `scripts/vault_bootstrap.py` |
| Ejecución local sin Docker (para pruebas) | `scripts/dev_local.py` |
| Pruebas automatizadas, de navegador y de carga | `tests/`, `scripts/carga.py` |
| Informe por módulo (este documento) y evidencias | `docs/`, `docs/evidencia/` |

## Brechas entre el front-end original y el backend (y cómo se cerraron)

| # | Brecha encontrada en el front-end original | Resolución |
|---|---|---|
| B1 | Catálogo, precios y stock salían de datos simulados en el navegador | Catálogo desde `inventory` vía `GET /api/v1/products` (S01); el total mostrado lo calcula el servidor |
| B2 | No existía cuenta ni sesión | Registro/ingreso/salida con cookie `HttpOnly` (S03–S06); el menú se dibuja según la sesión, pero la autorización real está en servidor |
| B3 | El «pago» y el estado del pedido se decidían en el navegador | El navegador solo abre la intención de pago; **«pagado» solo lo fija un resultado firmado del proveedor** que `orders` verifica (S14, S18, S19) |
| B4 | Formulario de contacto sin destino | `POST /contact` con validación y límite de frecuencia (S10); lectura solo para personal (S11) |
| B5 | Sin historial ni panel de operación | «Mis pedidos» y «Panel» consumen GraphQL, que agrega orders + inventory + clients (S20) |
| B6 | Sin administración de inventario | Pantalla de inventario con roles (S21–S24) |
| B7 | Datos se insertaban sin cuidado de XSS | Todo dato del servidor se inserta con `textContent`; no hay `innerHTML` con datos |

## Limitaciones declaradas (lo que NO se ejecutó o NO se afirma)

* **Docker, Vault y MongoDB reales no se ejecutaron en el entorno de desarrollo** (el entorno no tenía demonio de Docker ni acceso para descargar los binarios). El `docker-compose.yml` fue validado sintácticamente con `docker compose config`. Todas las pruebas se ejecutaron con **procesos reales** de cada servicio, pero la base fue **mongomock en memoria** y el cliente de Vault se probó contra un **servidor Vault KV v2 falso**. Por tanto, la persistencia real y el arranque con contenedores están **sin probar**; deben comprobarse en la máquina de demostración con la lista del Módulo 10.
* El proveedor de pagos es un **sandbox simulado** dentro de `payments` (no hay cuenta real); su protocolo de firma sí es el que se usaría con uno real.
* **Diagramas:** se entregan en formato editable (Mermaid `.mmd`, texto) y como imagen `.png`, en `docs/diagramas/`.
* El limitador de solicitudes es en memoria de proceso: válido para **una instancia** de gateway.
* **No se configuró TLS** (el enunciado lo pide para credenciales y datos restringidos): en producción va un proxy con HTTPS y `LR_COOKIE_SECURE=1`; está declarado como límite en el Módulo 10.
* Las mediciones de carga son de un entorno de desarrollo (2 vCPU, base en memoria), no de producción.
* Los usuarios y datos de prueba son **ficticios**; ninguna contraseña está en el repositorio (se generan en `deploy/.env`, que no se versiona).
