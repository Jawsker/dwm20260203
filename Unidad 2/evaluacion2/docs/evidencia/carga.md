# Reporte de carga (Módulo 9)

**Tipo de dato: MEDICIÓN** en el stack local de desarrollo (ver limitaciones). Los objetivos son una **proyección** declarada antes de medir.

## Entorno y método

- Máquina: Linux-6.18.44-fc-v338-x86_64-with-glibc2.39, 2 vCPU, 7.8 GiB RAM; Python 3.13.18.
- Sistema: 7 procesos (gateway, auth, clients, inventory, orders, payments, graphql) con base **mongomock en memoria** (sin red ni disco).
- Generador de carga en la misma máquina: 25 clientes concurrentes con sesión propia; 12 s por fase; límites de solicitudes del gateway desactivados.
- Datos: 12 productos con stock alto; pedidos creados por la propia fase de escritura (entre 1 y 3 líneas).
- Reproducir: `python scripts/carga.py --segundos 12 --concurrencia 25`.

## Resultados vs objetivos

| Operación | n | req/s | p50 ms | p95 ms | p99 ms | errores | objetivo p95 | veredicto |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| GET /products (anónimo) | 3845 | 320.1 | 73 | 133 | 163 | 0 | 300 | cumple |
| POST /graphql pedidos+productos | 946 | 78.1 | 324 | 436 | 485 | 0 | 500 | cumple |
| POST /orders | 337 | 27.2 | 254 | 489 | 527 | 0 | 800 | cumple |
| POST /orders/{id}/pay | 337 | 27.2 | 247 | 353 | 406 | 0 | 800 | cumple |
| POST sandbox-decision (webhook→payments→orders→inventory) | 337 | 27.2 | 387 | 570 | 669 | 0 | 1500 | cumple |
| POST /graphql panelOperacion (agregación, ver volumen) | 30 | — | 201 | 237 | 278 | 0 | 1000 | cumple |

Pedidos totales en la base al medir el panel: **5000** (proyección: ~200/día ≈ 73 000/año; este volumen equivale a ~25 días; la agregación es lineal en el número de pedidos, así que el año completo es una extrapolación NO medida).

## CPU y memoria por proceso

| Proceso | CPU media % | CPU máx % | RSS máx MiB |
|---|---:|---:|---:|
| gateway | 27 | 81 | 68 |
| auth | 16 | 150 | 130 |
| clients | 0 | 2 | 66 |
| inventory | 31 | 60 | 75 |
| orders | 59 | 94 | 117 |
| payments | 6 | 94 | 125 |
| graphql | 6 | 76 | 76 |
| **suma de servicios** | 145 | 184 | — |

(100 % = un núcleo completo; el generador de carga no está incluido en la tabla.)

## Limitaciones

- mongomock no refleja la latencia de MongoDB real (red, disco, índices): las cifras de base de datos son **optimistas**.
- Generador y sistema comparten CPU: las latencias son **pesimistas** por esa competencia. Ambos sesgos se compensan solo en parte.
- Una sola ejecución sin calentamiento dedicado; no hay intervalos de confianza. Repetir en el entorno de despliegue real antes de afirmar capacidad de producción.
- Fuera de alcance de la medición: red entre contenedores, TLS, Vault real (el cliente de secretos cachea 5 min).
