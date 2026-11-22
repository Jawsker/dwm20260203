# Guion del video · módulo «Crear pedido» de punta a punta

**Módulo elegido:** crear un pedido. Es el que pasa por todas las piezas: navegador → contenedor *frontend* → contenedor *gateway* → *auth* (sesión) → *orders* → *inventory* → *MongoDB*, con los secretos en *Vault*.

Duración sugerida: 5 a 7 minutos. Todo lo que se ve en pantalla son datos ficticios.

## 0. Antes de grabar (una sola vez)

1. Instala **Docker Desktop** y ábrelo (debe decir *Engine running*).
2. Abre una terminal en la carpeta `Unidad 2/evaluacion2` y ejecuta:
   ```bat
   python scripts\init_env.py
   docker compose -f deploy/docker-compose.yml up --build -d
   docker compose -f deploy/docker-compose.yml ps
   ```
   La primera vez tarda varios minutos. Todos los servicios deben quedar `running` o `healthy`, y `bootstrap` como `exited (0)`.
3. Busca la contraseña de prueba en `deploy\.env` (línea `LR_SEED_PASSWORD=`).
4. Abre **tres terminales** en `Unidad 2/evaluacion2` y deja corriendo en cada una:
   ```bat
   docker compose -f deploy/docker-compose.yml logs -f --since 1s gateway | python scripts\ver_logs.py
   ```
   ```bat
   docker compose -f deploy/docker-compose.yml logs -f --since 1s auth | python scripts\ver_logs.py
   ```
   ```bat
   docker compose -f deploy/docker-compose.yml logs -f --since 1s orders inventory | python scripts\ver_logs.py
   ```
   `ver_logs.py` convierte cada registro JSON en una línea legible: `hora · servicio · cid · mensaje`. El **cid** (id de correlación) es el mismo en todos los servicios que atendieron una misma acción del navegador: úsalo en el video para mostrar que es la misma solicitud.

Si algo falla al levantar, `docker compose -f deploy/docker-compose.yml logs bootstrap` muestra el motivo.

## 1. Contenedor Frontend → llama al API Gateway

1. Muestra en Docker Desktop (o con `docker compose ps`) los contenedores: `frontend`, `gateway`, `auth`, `orders`, `inventory`, `mongo`, `vault`…
2. Abre `http://localhost:8080` (lo sirve el contenedor **frontend**). Pulsa **F12 → Red (Network)** y escribe `api/v1` en el filtro.
3. Pulsa **Acceder** e inicia sesión con `ana@ejemplo.cl` y la contraseña de prueba.
4. En Red aparece `POST http://localhost:8000/api/v1/auth/login`. Haz clic y muestra:
   * **URL de la solicitud:** puerto **8000** = API Gateway (no el sitio, no un backend).
   * **Cuerpo enviado:** solo correo y contraseña.
   * **Respuesta:** cabecera `Set-Cookie: lr_session=…; HttpOnly` y cabecera `X-Correlation-Id`.
5. Ve a **Productos**, agrega 2 productos y pulsa **Confirmar y pagar**.
6. En Red aparece `POST http://localhost:8000/api/v1/orders`. Muestra que el cuerpo lleva **solo ids y cantidades** (ningún precio) y que la respuesta trae el **total calculado por el servidor**. Anota el `X-Correlation-Id` de la respuesta.

## 2. Contenedor ApiGateway → pide validación a Auth y enruta

En la terminal del **gateway**, con el mismo cid del paso 1.6, se lee:

```
gateway → auth-service: validando la sesión (cookie HttpOnly)
gateway: auth-service validó la sesión → usuario u_ana, rol customer
gateway: autorización OK en S12: rol customer permitido
gateway: enrutando S12 → orders POST /internal/orders (clave de servicio edge/gateway__orders desde el gestor de secretos)
gateway: orders respondió 201 a S12
```

Explica: el gateway **no decide quién eres**, se lo pregunta a Auth; después verifica que tu rol puede usar esa ruta (S12) y la **enruta** al backend dueño (orders) con la clave de servicio que obtiene de **Vault**. Si el gateway acaba de arrancar verás también `secreto 'edge/gateway__orders' leído desde Vault`.

**Caso denegado (opcional, 20 segundos):** con Ana abre `http://localhost:8080/admin.php`. En el gateway aparece `autorización DENEGADA … rol customer no está en ['staff', 'admin'] → 403`, sin llegar al backend.

## 3. Contenedor Auth Service → valida antes del enrutamiento

En la terminal de **auth**, con el mismo cid, y **antes** de la línea «enrutando» del gateway:

```
auth: clave de servicio de 'gateway' verificada con el secreto edge/gateway__auth → llamada PERMITIDA
auth-service: autenticación OK → sesión válida de u_ana; autorización: rol actual customer
```

Explica: Auth comprueba la sesión (guardada como hash SHA-256, nunca la cookie en claro) y entrega el **rol actual** del usuario. Al iniciar sesión se vio también `auth-service: inicio de sesión OK de u_ana (rol customer)`.

## 4. Contenedor Backend → acepta o rechaza verificando sus secretos

En la terminal de **orders / inventory**:

```
orders: clave de servicio de 'gateway' verificada con el secreto edge/gateway__orders → llamada PERMITIDA
inventory: clave de servicio de 'orders' verificada con el secreto edge/orders__inventory → llamada PERMITIDA
```

**Mostrar un rechazo** (lo más convincente): desde otra terminal, una llamada directa a orders con una clave falsa, como si alguien se saltara el gateway:

```bat
docker compose -f deploy/docker-compose.yml exec gateway python -c "import httpx; r = httpx.post('http://orders:9100/internal/orders', json={}, headers={'X-Edge-Caller': 'gateway', 'X-Edge-Key': 'clave-falsa'}); print(r.status_code, r.text)"
```

Responde `401 edge_unauthorized` y en el log de orders aparece:

```
orders: llamada RECHAZADA, la clave de 'gateway' no coincide con el secreto edge/gateway__orders ⚠
```

Explica: cada backend conoce **solo** las claves de quienes tienen permiso para llamarlo (están en Vault). Sin la clave correcta, rechaza la llamada aunque venga desde dentro de la red.

## 5. Contenedor Persistencia → el backend consultó y modificó la base

En la terminal de **orders / inventory**, con el mismo cid:

```
MongoDB inventory.products: consulta (find)                      ← precios vigentes
MongoDB orders.orders: inserción (insert)
orders: pedido LR-XXXXXXXX guardado en la base (colección orders) con total $… calculado en el servidor
MongoDB inventory.products: modificación (update)                ← descuenta stock disponible
MongoDB inventory.reservations: inserción (insert)
inventory: stock reservado para LR-XXXXXXXX (colecciones products y reservations): {...}
```

Para mostrarlo **dentro del contenedor de la base**: en Docker Desktop abre el contenedor `mongo` → pestaña **Exec** y escribe:

```
mongosh -u $MONGO_INITDB_ROOT_USERNAME -p $MONGO_INITDB_ROOT_PASSWORD --quiet
use orders
db.orders.find({}, {status: 1, total: 1, items: 1}).sort({created_at: -1}).limit(1)
```

Debe aparecer el mismo pedido `LR-…` con su total y estado `awaiting_payment`.

## Cierre (15 segundos)

Repite en voz alta el recorrido con el cid: *navegador → frontend → gateway (pide validación a Auth, autoriza, enruta con la clave de Vault) → orders (verifica la clave, guarda en MongoDB) → inventory (verifica la clave, reserva stock)*.

## Si algo no aparece

* **No hay líneas en ver_logs:** quita `| python scripts\ver_logs.py` para ver el JSON crudo; si tampoco aparece nada, el servicio no recibió la solicitud (revisa en Red que vaya a `localhost:8000`).
* **El login falla con 403 `csrf_origin`:** abre el sitio en `http://localhost:8080` (o `http://127.0.0.1:8080`), no por otro puerto ni por la IP de la red.
* **No se ve «leído desde Vault»:** es normal si el servicio ya leyó ese secreto (queda 5 minutos en caché). Para verlo: `docker compose -f deploy/docker-compose.yml restart gateway` y repite la acción.
