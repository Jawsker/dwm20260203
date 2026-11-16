# Libre & Rico · Evaluación 2 · Backend seguro completo

**Autor:** Matías Palma Santana (integrante único) · Universidad Andrés Bello · Desarrollo Web y Móvil · Entrega 09-11-2026

## Qué es

Libre & Rico es una panadería ficticia sin gluten. En la Evaluación 1 hice el sitio (PHP + Bootstrap + JavaScript) con un servicio simulado. En esta evaluación construí el **backend real** y conecté el sitio a él: ya no hay datos simulados, el catálogo, las cuentas, los pedidos y los pagos pasan por el servidor.

Idea central: **el navegador no decide nada importante.** El precio, el total, si un pago llegó y qué puede ver cada persona los decide el servidor.

```
Navegador ──► API Gateway :8000 ──► Auth Service :8100
                    │                Inventory :9000 · Orders :9100 · Clients :9200 · Payments :9300
                    └──────────────► GraphQL Gateway :8090 (solo lectura, junta datos de varios servicios)
Orders ──► cola STOMP /queue/pedidos :61613 ──► consumidor de tienda
Vault :8200 (secretos) · MongoDB :27017 (una base por servicio)
```

## Estructura (misma forma que el material del curso)

| Carpeta | Pieza | Puerto |
|---|---|---:|
| `apigateway/gateway/` | API Gateway (`gateway.py`, tabla de rutas en `routes.py`) | 8000 |
| `apigateway/auth-service/` | Servicio de autenticación (`auth_service.py`) | 8100 |
| `apigateway/inventory/`, `orders/`, `clients/`, `payments/` | Backends privados (`backend_api.py` en cada uno) | 9000, 9100, 9200, 9300 |
| `apigateway/common/` | Código compartido: secretos, registros, base de datos, cliente HTTP, mensajería | — |
| `graphql/` | GraphQL Gateway privado (`server.py`) | 8090 |
| `stomp/` | `productor.py` y `consumidor.py` de la cola `/queue/pedidos` | 61613 |
| `frontend/` | Sitio PHP + Bootstrap + JS | 8080 |
| `deploy/`, `scripts/`, `tests/`, `docs/` | Despliegue, utilidades, pruebas e informe | — |

Cada pieza es un proceso separado en su propio puerto. Solo el gateway (8000) y el sitio (8080) se exponen; el resto es privado.

## Decisiones que tomé y por qué

- **FastAPI + MongoDB:** el enunciado no fija la base de datos; elegí MongoDB por simplicidad con documentos como pedidos y productos, y FastAPI por rapidez para armar servicios y validar datos.
- **Un API Gateway como única puerta:** controla sesión, rol, frecuencia de uso y origen; los demás servicios no se exponen a Internet.
- **Un servicio por responsabilidad con su propia base:** si uno falla o es atacado, no da acceso a los datos de otro.
- **Secretos en Vault, no en el código:** cada servicio solo puede leer sus propias claves.
- **Precios y «pagado» los decide el servidor:** el pedido guarda el precio del catálogo y un pago solo se confirma con un aviso firmado del proveedor (webhook con HMAC).
- **GraphQL solo para leer y juntar datos** (por ejemplo «Mis pedidos» une pedidos, productos y cliente en una sola consulta).
- **Mensajería STOMP solo como aviso:** Orders publica «pedido pagado» en `/queue/pedidos` para la tienda; el mensaje no lleva datos personales y, si el broker falla, el pedido igual queda pagado.
- **Misma paleta en todo el sitio:** las pantallas conectadas al backend (acceso, pago, mis pedidos, panel) usan los siete colores definidos para el sitio (monocromática, base `#AA5439`), reemplazando los colores por defecto de Bootstrap.
- **No usé gRPC ni un servicio de analítica aparte:** la carga esperada es baja y las mediciones cumplen con holgura (ADR en el Módulo 9).

## Cómo ejecutarlo

**Con Docker** (despliegue completo con Vault y MongoDB):
```bash
cd "Unidad 2/evaluacion2"
python scripts/init_env.py                              # crea deploy/.env con claves al azar
docker compose -f deploy/docker-compose.yml up --build
# Sitio: http://localhost:8080      API: http://localhost:8000/api/v1
```

**Local por procesos, rápido** (base en memoria y secretos generados al arrancar):
```bash
pip install -r apigateway/requirements.txt -r apigateway/requirements-dev.txt
python scripts/dev_local.py          # levanta las 7 piezas, cada una en su puerto; imprime la contraseña de prueba
php -S localhost:8080 -t frontend    # en otra terminal
```

**Local por procesos con Vault y MongoDB reales** (como en clases):
```bash
vault server -dev -dev-root-token-id=mi-token-local     # terminal 1 → :8200
mongod                                                  # terminal 2 → :27017
export VAULT_TOKEN=mi-token-local LR_SEED_PASSWORD='una-clave-de-prueba'
python scripts/dev_local.py --real                      # terminal 3: crea secretos en Vault y levanta cada pieza
```
También se puede levantar cada pieza a mano, por ejemplo `uvicorn gateway:app --app-dir apigateway/gateway --port 8000` (tabla completa en `docs/modulos/10-backend-integracion.md`).

**Probar con token Bearer** (sin navegador):
```bash
TOKEN=$(curl -s localhost:8000/api/v1/auth/token -H 'Content-Type: application/json' \
        -d '{"email":"ana@ejemplo.cl","password":"<contraseña de prueba>"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s localhost:8000/api/v1/auth/session -H "Authorization: Bearer $TOKEN"
```
El sitio web no usa Bearer: el navegador recibe una cookie `HttpOnly` que JavaScript no puede leer.

**Mensajería STOMP** (con un broker en `127.0.0.1:61613`, por ejemplo RabbitMQ con `rabbitmq_stomp`):
```bash
export STOMP_USUARIO=... STOMP_CLAVE=...
python stomp/consumidor.py                 # escucha /queue/pedidos
python stomp/productor.py --formato json   # envía un evento de prueba
```
En el sistema, Orders publica el evento al confirmarse un pago (define `STOMP_USER` y `STOMP_PASSWORD` antes de `dev_local.py --real`, o usa Docker).

**Usuarios de prueba** (ficticios; la contraseña la imprime `dev_local.py` o está en `LR_SEED_PASSWORD` de `deploy/.env`):
`ana@ejemplo.cl` y `beto@ejemplo.cl` (clientes), `tienda@libreyrico.test` (personal), `admin@libreyrico.test`, `auditoria@libreyrico.test`.

**Pruebas:** `pytest tests` (41 pruebas) · `python tests/browser_e2e.py` (navegador) · `python scripts/carga.py` (carga).

## Dónde está cada entregable

El informe completo está en [`docs/INFORME.md`](docs/INFORME.md); cada módulo también está por separado.

| Módulo | Qué contiene | Archivo |
|---|---|---|
| Portada | caso, autor, versión del front-end, brechas y limitaciones | `docs/modulos/00-portada-y-brechas.md` |
| 1 | servicios, matriz de servicios y contratos JSON | `docs/modulos/01-servicios-y-contratos.md` · `docs/generado/m1-matriz-servicios.md` |
| 2 | modelo de dominio UML, cardinalidades y reglas de negocio | `docs/modulos/02-dominio-uml.md` · `docs/diagramas/dominio.png` |
| 3 | matriz de sistemas, mapa de componentes, secuencia de compra | `docs/modulos/03-sistemas-integracion.md` · `docs/diagramas/componentes.png`, `secuencia_compra.png` |
| 4 | actores y matriz de permisos por ruta y rol | `docs/modulos/04-stakeholders-permisos.md` · `docs/generado/m4-permisos.md` |
| 5 | UML del gateway y fronteras de confianza | `docs/modulos/05-gateway-uml-confianza.md` · `docs/diagramas/gateway_uml.png`, `fronteras_confianza.png` |
| 6 | matriz de rutas, inventario de secretos y operaciones GraphQL | `docs/modulos/06-rutas-y-secretos.md` · `docs/generado/m6-rutas.md`, `m6-secretos.md` |
| 7 | clasificación de datos, decisión sobre secretos del cliente, validaciones V1–V6 | `docs/modulos/07-datos-sensibles.md` · `docs/evidencia/resultados-pruebas.md` |
| 8 | servicios privados, esquema GraphQL, ejemplos reales de consulta | `docs/modulos/08-privado-graphql.md` · `docs/evidencia/ejemplos-graphql.md` |
| 9 | ADR sobre analítica y gRPC + mediciones de carga | `docs/modulos/09-adr-analitica-grpc.md` · `docs/evidencia/carga.md` |
| 10 | trazabilidad requisito → pantalla → servicio → prueba → resultado, y demostración | `docs/modulos/10-backend-integracion.md` · `docs/generado/m10-trazabilidad.md` |
| Extra | explicación simple del proyecto | `docs/GUIA-PARA-ENTENDER.md` |

Capturas del sitio funcionando: `docs/evidencia/capturas/`.

## Qué probé y qué no

| Probado | Resultado |
|---|---|
| Servicios, reglas de seguridad, token Bearer y mensajería STOMP (`pytest`) | 41 de 41 pruebas OK |
| Sitio completo en navegador (Playwright) | 20 de 20 OK, con capturas |
| Carga (25 usuarios simultáneos) | todos los tiempos dentro de los objetivos, 0 errores |

**No probado:** `docker compose`, el modo `--real`, Vault real, MongoDB real y RabbitMQ no los pude ejecutar en mi entorno de desarrollo (la mensajería se probó con un broker STOMP en memoria). Las pruebas usaron una base en memoria y un Vault simulado, así que la persistencia real y el arranque con contenedores están sin verificar (la lista para comprobarlo está en el Módulo 10). El proveedor de pagos es un **sandbox simulado**; su firma sí funciona como la de uno real.

**Límites conocidos:** el limitador de peticiones sirve para una sola instancia del gateway, no configuré HTTPS (en producción iría detrás de un proxy con TLS) y las mediciones son de un entorno de desarrollo.

## Uso de IA: prompts utilizados y resultados (APA 7)

Desarrollé este proyecto con asistencia de Claude (Anthropic, 2026a, 2026b), uso permitido en el curso. Abajo están los prompts principales, textuales, y qué resultado dio cada uno. Revisé los resultados y las limitaciones están declaradas en la sección anterior.

| # | Fecha | Prompt (textual) | Resultado |
|---|---|---|---|
| 1 | 09-11-2026 | «@Evaluacion_1.pdf por favor modifica el codigo para que cumpla con lo siguiente:» | Catálogo y pedido dinámicos en el front-end con un servicio simulado (Evaluación 1, carpeta `Test/Entrega v.1`). |
| 2 | 09-11-2026 | «una consulta. el profesor pide incorporar esto: https://www.connectionstrings.com/ para que sirve?» | Explicación del sitio; el formato de cadena de conexión de MongoDB se usó en las credenciales por servicio guardadas en Vault. |
| 3 | 09-11-2026 | «@Evaluacion_2.pdf @AutenticacionAutorizacion_-_copia.pdf @Desarrollo_Web_Movil-1.pdf a continuación te muestro lo solicitado en los requisitos que me han pedido cumplir para la proxima entrega y otros documentos de cosas que deben incorporarse» | Backend de la Evaluación 2: gateway, autenticación, inventory, orders, clients, payments y GraphQL; integración con el sitio; pruebas automáticas, de navegador y de carga; informe por módulos. |
| 4 | 09-11-2026 | «Por favor escribe el readme ya que no me quedan muchos minutos para entregar el trabajo.» | Primera versión de este README. |
| 5 | 09-11-2026 | «estos son los requisitos actuales» (con el PDF de la Evaluación 2) | Revisión contra el enunciado y cierre de faltantes: ejemplo real de cada contrato, UML de servicios, matrices ampliadas, recorridos y guion de demostración. |
| 6 | 16-11-2026 | «Necesito comparar mi repo con el hecho por el profe en esta url https://github.com/evivanco/dwm20260203.git y que me comentes si mi trabajo cumple con lo que el especificó: "deben tener las piezas y separacion de infraestructura adecuada. usar los colores previamente establecidos para el backend y citar en apa 7 qué promt utilizamos y que resultados dio"» | Comparación pieza por pieza: faltaban la mensajería STOMP, la paleta en las pantallas del backend y esta cita. |
| 7 | 16-11-2026 | «deseo que la infraestructura sea similar a la del profesor. la paleta de colores de la pagina es esta Elegida en Paletton, esquema monocromático a partir del color base #AA5439 […]» | Carpetas y puertos como el material del curso, ejecución por procesos, token Bearer, mensajería STOMP y paleta única en el front-end. |

**Referencias**

Anthropic. (2026a). *Claude Sonnet 5.5* (versión de noviembre de 2026) [Modelo de lenguaje de gran tamaño]. https://claude.ai

Anthropic. (2026b). *Claude Fable 5.2* (versión de noviembre de 2026) [Modelo de lenguaje de gran tamaño]. https://claude.ai

Vivanco, E. (2026). *dwm20260203* [Repositorio de código]. GitHub. https://github.com/evivanco/dwm20260203

Los prompts 1 a 5 se hicieron con Claude Sonnet 5.5 y los prompts 6 y 7 con Claude Fable 5.2 (identificadores configurados en la sesión: `claude-sonnet-5-5` y `claude-fable-5-2`). Los datos, usuarios y marcas del proyecto son ficticios.
