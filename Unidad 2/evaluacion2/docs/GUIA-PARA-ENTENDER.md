# Guía para entender y explicar el proyecto (en simple)

Pensada para estudiar en una hora. Si entiendes las secciones 1 a 4, puedes defender el proyecto.

## 1. La idea en una frase

Una tienda online de panadería donde **el navegador nunca decide nada importante**: ni el precio, ni si un pago llegó, ni quién eres. Todo eso lo decide el servidor, y cada pieza del servidor desconfía de las demás.

## 2. La panadería como analogía

| En el sistema | En la panadería | Qué hace |
|---|---|---|
| **API Gateway** | La recepción | Única puerta de entrada. Pide tu credencial, revisa que puedas pasar y te deriva |
| **Auth** | El control de identidad | Guarda cuentas y contraseñas; dice «este es Ana, cliente» |
| **Clients** | La ficha de clientes | Nombre, teléfono, dirección; mensajes de contacto |
| **Inventory** | La bodega | Catálogo, precios y stock; aparta producto para un pedido |
| **Orders** | El libro de pedidos | Crea pedidos, calcula el total, lleva su estado |
| **Payments** | La caja | Se conecta con el proveedor de pagos y recibe el resultado |
| **GraphQL** | El ayudante que junta papeles | Une datos de pedidos, bodega y clientes en una sola respuesta |
| **Vault** | La caja fuerte de llaves | Guarda las claves; cada servicio tiene permiso solo para las suyas |
| **MongoDB** | Los archivadores | Cada servicio tiene el suyo y no abre el de otro |

## 3. Los 4 flujos que debes saber contar

### A. Iniciar sesión
1. Ana escribe correo y contraseña → llega al **gateway**.
2. El gateway se lo pasa a **Auth**, que compara con el hash guardado (la contraseña nunca se guarda tal cual: se guarda un «resumen» irreversible, Argon2id).
3. Si coincide, Auth crea una **sesión** y el gateway entrega una **cookie `lr_session` HttpOnly**: el navegador la manda sola en cada petición, pero el JavaScript de la página **no puede leerla** (así un script malicioso no la roba).
4. Seguridad extra: tras 5 intentos fallidos se bloquea temporalmente; el mensaje de error es siempre el mismo («credenciales inválidas») para no revelar si el correo existe; la sesión caduca a los 30 min sin uso o a las 8 h.

### B. Hacer un pedido
1. El navegador envía **solo** `producto` y `cantidad`. **No envía precios ni total.**
2. **Orders** le pregunta a **Inventory** los precios actuales y calcula el total.
3. Inventory **aparta** (reserva) el stock de forma atómica: o aparta todo el pedido o nada, así dos clientes no compran la última unidad a la vez.
4. El pedido queda `awaiting_payment` y **vence en 15 minutos**; si vence, el stock vuelve a la bodega.
5. Si el cliente reintenta por un corte de internet, la **Idempotency-Key** evita que se cree un pedido duplicado.

### C. Pagar
1. El cliente pulsa «Pagar»: Orders le pide a Payments abrir un pago **por el monto del pedido guardado** (no por uno que mande el navegador).
2. El proveedor (aquí un sandbox simulado) paga o rechaza y avisa con un **webhook**: un mensaje del proveedor al servidor.
3. Como cualquiera podría falsificar ese aviso, va **firmado** (HMAC con un secreto compartido). Payments verifica: firma válida, mensaje reciente (±5 min), evento no repetido y monto exacto.
4. Solo entonces el pedido pasa a `paid` y el stock se descuenta de verdad. **La pantalla nunca dice «pagado» por sí sola**: pregunta al servidor.

### D. Quién ve qué (roles)
- **Cliente:** solo sus pedidos y su perfil. Si pide el pedido de otro, recibe «no encontrado» (ni siquiera confirma que existe).
- **Personal:** ve todos los pedidos, ajusta stock, lee mensajes; ve nombre y teléfono, no dirección.
- **Administración:** lo del personal + crear productos y cuentas de personal.
- **Auditoría:** solo lectura, sin datos personales.
- El gateway filtra por rol (primera barrera) y **cada servicio vuelve a verificar** (segunda barrera). Por eso se llama «defensa en profundidad».

## 4. ¿Por qué cada decisión? (respuestas listas)

| Pregunta probable | Respuesta corta |
|---|---|
| ¿Por qué un gateway? | Para tener una sola puerta que controla sesión, rol, tamaño, frecuencia y origen; los servicios internos no quedan expuestos |
| ¿Por qué cada servicio tiene su base? | Para que un fallo o ataque en uno no dé acceso a los datos de otro, y poder cambiarlos de forma independiente |
| ¿Qué es Vault y por qué? | Un gestor de secretos: las claves no van en el código ni en el repositorio; se pueden rotar y cada servicio solo lee las suyas |
| ¿Qué pasa si Vault se cae? | Usa el último valor conocido un tiempo limitado y luego falla cerrado (error 503); nunca usa una clave por defecto |
| ¿Por qué GraphQL aquí? | La pantalla «Mis pedidos» necesita pedidos + productos + cliente: GraphQL lo une en **una** petición en vez de tres. Es solo lectura |
| ¿Por qué no gRPC ni servicio de analítica? | La carga proyectada es baja (~200 pedidos/día) y las mediciones cumplen con holgura; añadir eso sería complejidad sin necesidad (ver ADR, Módulo 9) |
| ¿Qué es una cookie HttpOnly? | Una cookie que el navegador envía pero que el JavaScript no puede leer |
| ¿Qué es CSRF y cómo se evita? | Que otra página haga acciones con tu sesión. Se evita con cookie `SameSite=Lax` y verificando el `Origin` de cada petición que modifica datos |
| ¿Qué probaste? | 37 pruebas automáticas (incluye 6 validaciones del Módulo 7), 20 pruebas con navegador y una prueba de carga |
| ¿Qué NO probaste? | Docker/Vault/MongoDB reales (las pruebas usaron base en memoria y un Vault simulado) y un proveedor de pagos real |

## 5. Mini glosario

- **API:** puerta con reglas por la que un programa pide cosas a otro.
- **Endpoint / ruta:** una dirección concreta de esa puerta, por ejemplo `POST /orders`.
- **Hash:** resumen irreversible de un texto; sirve para comparar sin guardar el original.
- **Token / sesión:** comprobante temporal de que ya iniciaste sesión.
- **Webhook:** aviso automático de un sistema externo a tu servidor.
- **HMAC / firma:** código calculado con un secreto compartido que prueba que el mensaje no fue falsificado ni alterado.
- **Idempotencia:** repetir la misma petición no cambia el resultado (no duplica el pedido).
- **Rate limit:** tope de peticiones por minuto para frenar abusos.
- **ADR:** documento corto que explica una decisión y por qué se tomó.
- **p95:** el 95 % de las peticiones fue más rápido que ese tiempo.

## 6. Cómo verlo funcionar (20 minutos)

```bash
cd "Unidad 2/evaluacion2"
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python scripts/dev_local.py          # deja corriendo; imprime la contraseña de prueba
php -S localhost:8080 -t frontend    # en otra terminal
```
Abre `http://localhost:8080` y recorre: 1) crear cuenta, 2) comprar, 3) pagar → «Aprobar» (sandbox), 4) ver «Mis pedidos». Luego entra como `tienda@libreyrico.test` y revisa el panel, y como `auditoria@libreyrico.test` para ver que no ve datos personales.

## 7. Ejercicio de comprensión (cambia algo tú mismo)

1. Cambia el vencimiento del pedido de 15 a 1 minuto: en `backend/orders/main.py` línea `TTL = int(os.getenv("LR_ORDER_TTL_SECONDS", "900"))` pon `"60"` (reinicia `dev_local.py`), crea un pedido sin pagar y observa que expira y devuelve el stock.
2. Baja el límite de intentos de login: en `backend/auth/main.py` cambia `"LR_LOGIN_MAX_FAILS", "5"` por `"3"` (reinicia) y compruébalo con 4 contraseñas erróneas.
3. Ejecuta `pytest tests -q` y mira qué prueba falla si rompes una regla (por ejemplo, quita la verificación de rol de una ruta en `routes.py`).

Si puedes hacer esto y explicar por qué pasó lo que pasó, entiendes el proyecto.
