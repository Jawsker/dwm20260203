# Libre & Rico · Evaluación 2 · Backend seguro completo

**Autor:** Matías Palma Santana (integrante único) · Universidad Andrés Bello · Desarrollo Web y Móvil · Entrega 09-11-2026

## Qué es

Libre & Rico es una panadería ficticia sin gluten. En la Evaluación 1 hice el sitio (PHP + Bootstrap + JavaScript) con un servicio simulado. En esta evaluación construí el **backend real** y conecté el sitio a él: ya no hay datos simulados, el catálogo, las cuentas, los pedidos y los pagos pasan por el servidor.

Idea central: **el navegador no decide nada importante.** El precio, el total, si un pago llegó y qué puede ver cada persona los decide el servidor.

```
Navegador ──► API Gateway ──► Auth · Clients · Inventory · Orders · Payments · GraphQL   (red privada)
                                  └─► MongoDB (una base por servicio) · Vault (secretos)
```

## Decisiones que tomé y por qué

- **FastAPI + MongoDB:** el enunciado no fija la base de datos; elegí MongoDB por simplicidad con documentos como pedidos y productos, y FastAPI por rapidez para armar servicios y validar datos.
- **Un API Gateway como única puerta:** controla sesión, rol, frecuencia de uso y origen; los demás servicios no se exponen a Internet.
- **Un servicio por responsabilidad con su propia base:** si uno falla o es atacado, no da acceso a los datos de otro.
- **Secretos en Vault, no en el código:** cada servicio solo puede leer sus propias claves.
- **Precios y «pagado» los decide el servidor:** el pedido guarda el precio del catálogo y un pago solo se confirma con un aviso firmado del proveedor (webhook con HMAC).
- **GraphQL solo para leer y juntar datos** (por ejemplo «Mis pedidos» une pedidos, productos y cliente en una sola consulta).
- **No usé gRPC ni un servicio de analítica aparte:** la carga esperada es baja y las mediciones cumplen con holgura (ADR en el Módulo 9).

## Cómo ejecutarlo

**Con Docker** (despliegue completo con Vault y MongoDB):
```bash
cd "Unidad 2/evaluacion2"
python scripts/init_env.py                              # crea deploy/.env con claves al azar
docker compose -f deploy/docker-compose.yml up --build
# Sitio: http://localhost:8080      API: http://localhost:8000/api/v1
```

**Local sin Docker** (base en memoria, para probar rápido):
```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python scripts/dev_local.py          # deja los 7 servicios corriendo; imprime la contraseña de prueba
php -S localhost:8080 -t frontend    # en otra terminal
```

**Usuarios de prueba** (ficticios; la contraseña la imprime `dev_local.py` o está en `LR_SEED_PASSWORD` de `deploy/.env`):
`ana@ejemplo.cl` y `beto@ejemplo.cl` (clientes), `tienda@libreyrico.test` (personal), `admin@libreyrico.test`, `auditoria@libreyrico.test`.

**Pruebas:** `pytest tests` (37 pruebas) · `python tests/browser_e2e.py` (navegador) · `python scripts/carga.py` (carga).

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

Código: `backend/` (servicios), `frontend/` (sitio), `deploy/` (docker compose), `scripts/`, `tests/`. Capturas del sitio funcionando: `docs/evidencia/capturas/`.

## Qué probé y qué no

| Probado | Resultado |
|---|---|
| Servicios y reglas de seguridad (`pytest`) | 37 de 37 pruebas OK |
| Sitio completo en navegador (Playwright) | 20 de 20 OK, con capturas |
| Carga (25 usuarios simultáneos) | todos los tiempos dentro de los objetivos, 0 errores |

**No probado:** `docker compose`, Vault real y MongoDB real no los pude ejecutar en mi entorno de desarrollo. Las pruebas usaron una base en memoria y un Vault simulado, así que la persistencia real y el arranque con contenedores están sin verificar (la lista para comprobarlo está en el Módulo 10). El proveedor de pagos es un **sandbox simulado**; su firma sí funciona como la de uno real.

**Límites conocidos:** el limitador de peticiones sirve para una sola instancia del gateway, no configuré HTTPS (en producción iría detrás de un proxy con TLS) y las mediciones son de un entorno de desarrollo.

## Uso de IA

Desarrollé este proyecto con ayuda de Claude (asistente de IA), uso permitido en el curso. Los datos, usuarios y marcas son ficticios.
