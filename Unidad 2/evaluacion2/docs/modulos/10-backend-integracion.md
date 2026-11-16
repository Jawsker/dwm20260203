# Módulo 10 · Backend completo, integración y demostración

## Trazabilidad requisito → pantalla → servicio → prueba → resultado → evidencia

Generada por `python scripts/generar_docs.py` a partir de `docs/evidencia/junit.xml` y `resultados-navegador.json`: los resultados no se escriben a mano.

Pantallas: **P01** `productos.php` · **P02** modal de acceso (todas las páginas) · **P03** `pago.php` · **P04** `mis-pedidos.php` · **P05** `admin.php` · **P06** `contacto.php`.

{{incluir:generado/m10-trazabilidad.md}}

## Cómo ejecutar

Ver `README.md` (raíz de `evaluacion2`): arranque con `docker compose`, arranque local sin Docker, pruebas, prueba de navegador y carga.

## Lista de comprobación para la demostración (hacer en la máquina con Docker)

Esto **no se ejecutó** en el entorno de desarrollo; es lo que debe verificarse antes de presentar:

1. `python scripts/init_env.py` crea `deploy/.env`; `docker compose -f deploy/docker-compose.yml up --build` termina con `bootstrap` en estado *Exited (0)* y el resto *healthy*.
2. `curl http://localhost:8000/health` → 200; `curl http://localhost:8100/health` desde el anfitrión → **debe fallar** (sin puerto publicado).
3. Abrir `http://localhost:8080`, crear cuenta, comprar, pagar con el sandbox y ver «Pagado».
4. **Persistencia real:** `docker compose down` (sin `-v`) y `up` de nuevo: el pedido y el usuario siguen.
5. **Falla de Vault:** `docker compose stop vault` → el sistema sigue un tiempo con el último valor y luego responde 503; `start vault` → se recupera (en modo dev Vault pierde los secretos al reiniciarse: volver a ejecutar `bootstrap`).
6. `docker compose stop inventory` → catálogo/compra responden 503 controlado, el resto del sitio sigue.

## Documentación de operación

* **Arranque/parada:** `docker compose -f deploy/docker-compose.yml up -d --build` / `down`.
* **Configuración de secretos:** nada se escribe a mano: `init_env.py` genera la clave raíz de Vault, la de MongoDB y la contraseña de los usuarios de prueba en `deploy/.env` (no versionado); `vault_bootstrap.py` genera y reparte el resto.
* **Datos iniciales:** catálogo de 12 productos (`apigateway/inventory/catalogo.json`) y 5 usuarios ficticios (2 clientes, personal, admin, auditoría) con la contraseña de `LR_SEED_PASSWORD`.
* **Salud:** cada servicio expone `/health` (vivo) y `/ready` (base y dependencias).
* **Rotación de un secreto:** borrar su ruta en Vault y volver a ejecutar `bootstrap`; reiniciar los servicios implicados.
* **Registros:** JSON por salida estándar con `correlation_id` para seguir una solicitud entre servicios.

## Ejecución local por procesos (misma forma de trabajo que en clases)

| Pieza | Comando equivalente | Puerto |
|---|---|---:|
| Vault | `vault server -dev -dev-root-token-id=<token>` | 8200 |
| MongoDB | `mongod` | 27017 |
| Broker STOMP (opcional) | RabbitMQ con `rabbitmq_stomp` | 61613 |
| Gateway | `uvicorn gateway:app --app-dir apigateway/gateway --port 8000` | 8000 |
| Auth Service | `uvicorn auth_service:app --app-dir apigateway/auth-service --port 8100` | 8100 |
| Inventory / Orders / Clients / Payments | `uvicorn backend_api:app --app-dir apigateway/<servicio> --port 9000 / 9100 / 9200 / 9300` | 9000–9300 |
| GraphQL Gateway | `uvicorn server:app --app-dir graphql --port 8090` | 8090 |

`python scripts/dev_local.py --real` hace todo lo anterior de una vez (salvo Vault, MongoDB y el broker, que deben estar corriendo): ejecuta el bootstrap de secretos y levanta cada proceso con su propio token de Vault. **Este modo `--real` no se ejecutó en el entorno de desarrollo** (no había binarios de Vault ni MongoDB); `python scripts/dev_local.py` sin opciones (base en memoria y secretos por entorno) es el que usan las pruebas.

## Guion de demostración de los flujos principales (≈5 minutos)

1. **Visitante:** abrir el sitio → catálogo cargado desde el API (S01) → filtrar por categoría.
2. **Registro e ingreso:** «Acceder» → crear cuenta → el menú muestra el rol (S03, S06).
3. **Compra:** agregar productos → «Confirmar y pagar» → el **total lo calcula el servidor** (S12). Mostrar en las herramientas del navegador que la solicitud solo lleva ids y cantidades.
4. **Pago:** pantalla de pago → «Aprobar» (sandbox) → el pedido pasa a **Pagado** por el webhook firmado (S14, S18, S19).
5. **Mis pedidos (GraphQL):** historial con productos vigentes en una sola consulta (S20).
6. **Seguridad:** con otra cuenta pedir el pedido anterior → 404 sin datos; con el cliente intentar `admin.php` → aviso y 403 en la API.
7. **Personal:** entrar como `tienda@libreyrico.test` → avanzar el pedido a «En preparación» (S16), ajustar stock (S24).
8. **Auditoría:** entrar como `auditoria@libreyrico.test` → panel sin datos personales (error parcial en bajo stock, esperado).

Evidencia equivalente ya capturada: `docs/evidencia/capturas/` y `resultados-navegador.json`.

## Flujos complementarios y alcance

* **Mensajería:** aviso interno «pedido pagado» por STOMP (Módulo 3). **Despacho y boletas:** no aplican al caso (retiro en tienda).
* **Restricciones tecnológicas del curso:** se mantienen PHP + Bootstrap + JavaScript en el front-end; el backend usa Python/FastAPI, MongoDB y Vault.
* **Persistencia, esquema y datos de prueba:** MongoDB real en el despliegue (volumen `mongo-data`); los servicios crean sus **índices al arrancar** (colecciones sin esquema fijo; la validación está en el servicio); los datos de prueba se crean con `LR_SEED=1` (productos de `catalogo.json` y 5 usuarios ficticios). Dependencias con **versiones fijadas** en `apigateway/requirements.txt`; variables en `deploy/.env.example` sin valores reales.
* **Pruebas gRPC/analíticas:** no aplican (ver ADR del Módulo 9).

## Límites declarados de esta entrega

* **TLS:** las comunicaciones del entorno de desarrollo y del compose van en HTTP dentro de la red privada; el enunciado pide TLS para credenciales y datos restringidos. En producción debe ir un proxy con HTTPS delante del gateway (`LR_COOKIE_SECURE=1`) y TLS/mTLS entre servicios; **no está implementado ni probado** aquí.
* **Docker, Vault y MongoDB reales:** no se ejecutaron en el entorno de desarrollo (ver portada y lista de comprobación); las pruebas usan procesos reales de cada servicio con base en memoria y un Vault simulado.
* **Proveedor de pagos:** adaptador de prueba que conserva contrato, autenticación (firma) y transiciones, como pide el enunciado.
* **Retención de mensajes de contacto:** sin purga automática (Módulo 7).
