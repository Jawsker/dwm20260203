# Módulo 9 · ADR-001 · Analítica separada y gRPC: no se adoptan (por ahora)

**Estado:** aceptada · **Fecha:** 09-11-2026 · **Decide:** Matías Palma Santana

## Contexto

Libre & Rico es una panadería con venta web de retiro en tienda. La **carga proyectada** (supuesto declarado, no medido en producción): ~200 pedidos/día, pico ~30 pedidos/hora, ~20 clientes simultáneos, ~73 000 pedidos/año. Se evaluó (a) un servicio de **analítica separado** (almacén/ETL propio) y (b) **gRPC** para la comunicación interna.

## Matriz de necesidades

| Característica | Valor (proyección salvo indicación) | Implica |
|---|---|---|
| Volumen de datos | ~200 pedidos/día; ~73 000 pedidos/año; panel medido con **5 000** pedidos | una base transaccional basta; no hace falta almacén aparte |
| Concurrencia | ~20 clientes simultáneos (proyección); **25 medidos** | no requiere escalar horizontalmente |
| Tamaño de mensajes | < 5 KB por solicitud (cuerpo máximo por ruta en el gateway: pequeño) | sin necesidad de serialización binaria |
| Frecuencia | pico ~30 pedidos/hora | una operación cada pocos minutos; sin tráfico interno masivo |
| Latencia esperada | catálogo ≤ 300 ms, pedido/pago ≤ 800 ms, confirmación ≤ 1,5 s, panel ≤ 1 s (p95) | cumplido con holgura (ver abajo) |
| Streaming | **no** hay flujo continuo; el front-end consulta el estado del pedido con GET | gRPC con streaming no se justifica |
| Agregaciones | pedidos por estado, ventas pagadas, bajo stock | una consulta `$group` en `orders` |
| Datos personales en analítica | no se usan: el panel muestra conteos y montos, no personas | sin necesidad de pseudonimización |

## Decisión

1. **No se crea un servicio de analítica separado.** Las necesidades actuales (pedidos por estado, ventas pagadas, productos con bajo stock) se resuelven con **agregación en la base de `orders` (`$group`)** a través de GraphQL (`panelOperacion`).
2. **No se adopta gRPC.** La comunicación interna sigue en HTTP/JSON con claves por arista.

## Justificación con mediciones

Medición en entorno de desarrollo (2 vCPU, base en memoria; método y limitaciones en `docs/evidencia/carga.md`), 25 clientes concurrentes —más del doble de lo proyectado—:

| Operación | p95 medido | Objetivo p95 |
|---|---:|---:|
| Catálogo | 133 ms | 300 ms |
| GraphQL pedidos+productos | 436 ms | 500 ms |
| Crear pedido | 489 ms | 800 ms |
| Pagar | 353 ms | 800 ms |
| Confirmar pago (webhook→payments→orders→inventory) | 570 ms | 1500 ms |
| Panel con **5 000 pedidos** | 237 ms | 1000 ms |

Todos los objetivos se cumplen con 0 errores. El tráfico proyectado (≈ una solicitud cada pocos segundos en el pico) es muy inferior al medido (cientos por segundo en lectura). El panel es lineal en el número de pedidos: 5 000 pedidos ≈ 25 días de operación; el año completo (~73 000) es una **extrapolación NO medida**.

**gRPC** reduce latencia/serialización en llamadas internas de alto volumen; aquí cada pedido implica pocas llamadas internas y el tiempo se reparte entre varias, sin un cuello de botella de transporte que justifique perder la simplicidad de depuración (JSON legible, mismos errores y correlación) y añadir contratos `.proto`, generación de código y balanceo HTTP/2.

**Analítica separada** se justificaría por consultas históricas pesadas, cruces multi-fuente o impacto en la base transaccional. Hoy no ocurre: una sola consulta agregada sobre un volumen pequeño.

## Consecuencias

* (+) Menos piezas que operar, asegurar y desplegar; mismo modelo de errores, trazas y claves en todo el sistema.
* (−) Si crece el volumen o aparecen informes históricos, el panel se degradará linealmente.
* (−) El proveedor de pagos real puede añadir latencia que esta medición (sandbox local) no captura.

## Condiciones para revisar la decisión

* p95 del panel > 1 s con el volumen real, o > 5 000 pedidos/día sostenidos.
* Necesidad de informes históricos/cohortes sin afectar la base transaccional → analítica separada (réplica de lectura o almacén).
* Más de ~10 llamadas internas por solicitud externa o CPU dominada por (de)serialización → evaluar gRPC en esas aristas.

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Servicio de analítica con ETL | coste operativo sin necesidad actual |
| gRPC en todas las aristas | complejidad sin cuello de botella medido |
| Cache de agregados | añade invalidación; no necesario con p95 237 ms |

## Carga medida (copia)

{{incluir:evidencia/carga.md}}
