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
2. `curl http://localhost:8000/health` → 200; `curl http://localhost:8001/health` desde el anfitrión → **debe fallar** (sin puerto publicado).
3. Abrir `http://localhost:8080`, crear cuenta, comprar, pagar con el sandbox y ver «Pagado».
4. **Persistencia real:** `docker compose down` (sin `-v`) y `up` de nuevo: el pedido y el usuario siguen.
5. **Falla de Vault:** `docker compose stop vault` → el sistema sigue un tiempo con el último valor y luego responde 503; `start vault` → se recupera (en modo dev Vault pierde los secretos al reiniciarse: volver a ejecutar `bootstrap`).
6. `docker compose stop inventory` → catálogo/compra responden 503 controlado, el resto del sitio sigue.

## Documentación de operación

* **Arranque/parada:** `docker compose -f deploy/docker-compose.yml up -d --build` / `down`.
* **Configuración de secretos:** nada se escribe a mano: `init_env.py` genera la clave raíz de Vault, la de MongoDB y la contraseña de los usuarios de prueba en `deploy/.env` (no versionado); `vault_bootstrap.py` genera y reparte el resto.
* **Datos iniciales:** catálogo de 12 productos (`backend/inventory/catalogo.json`) y 5 usuarios ficticios (2 clientes, personal, admin, auditoría) con la contraseña de `LR_SEED_PASSWORD`.
* **Salud:** cada servicio expone `/health` (vivo) y `/ready` (base y dependencias).
* **Rotación de un secreto:** borrar su ruta en Vault y volver a ejecutar `bootstrap`; reiniciar los servicios implicados.
* **Registros:** JSON por salida estándar con `correlation_id` para seguir una solicitud entre servicios.
