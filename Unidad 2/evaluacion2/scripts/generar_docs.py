#!/usr/bin/env python3
"""Genera las matrices del informe DESDE el código (routes.py, topology.py) y los resultados de pruebas.

Así la documentación no puede divergir de la implementación: si cambia una ruta, cambia la matriz.
Uso:  python scripts/generar_docs.py            (usa docs/evidencia/junit.xml si existe)
      python scripts/generar_docs.py --pruebas  (ejecuta pytest primero y guarda junit.xml)
"""
from __future__ import annotations

import ast
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "gateway"))
sys.path.insert(0, str(ROOT / "backend" / "common"))
sys.path.insert(0, str(ROOT / "scripts"))
from routes import PREFIX, ROUTES  # noqa: E402
from topology import EDGES, EXTRA, WITH_DB  # noqa: E402

GEN = ROOT / "docs" / "generado"
EVI = ROOT / "docs" / "evidencia"
GEN.mkdir(exist_ok=True, parents=True)
EVI.mkdir(exist_ok=True, parents=True)

# id: (requisito, pantalla y acción, propósito, entrada, salida/errores, clasificación de datos, condición de propiedad)
META = {
    "S01": ("RF1 RF2", "P01 · cargar catálogo / filtrar", "Consultar catálogo", "query: categoria?, q?, available?, limit 1-100, offset ≥0",
            "200 {items[{id,categoria,emoji,nombre,descripcion,precio,disponible}],total,categorias}; 400 invalid_filter; 429", "Público", "—"),
    "S02": ("RF1", "P01 · detalle de producto", "Consultar un producto", "ruta: product_id", "200 producto; 404", "Público", "—"),
    "S03": ("RF6", "P02 · crear cuenta", "Registrar cliente y abrir sesión",
            "body: email, password 10-128, nombre 2-80, telefono?", "201 {user:{id,email,role}} + cookie; 400 validation_error; 409 email_taken; 429", "Credencial + dato personal", "El rol lo fija el servidor (customer)"),
    "S04": ("RF6", "P02 · ingresar", "Autenticar", "body: email, password", "200 {user} + cookie HttpOnly; 401 invalid_credentials; 429 too_many_attempts", "Credencial", "—"),
    "S05": ("RF6", "Menú de cuenta · cerrar sesión", "Revocar la sesión", "cookie", "204 (cookie borrada); 401", "Credencial", "Solo su propia sesión"),
    "S06": ("RF6", "Todas · estado de sesión", "Saber quién soy", "cookie", "200 {user_id,role,email}; 401", "Dato personal (correo)", "Solo la propia"),
    "S07": ("RF8", "P04 · perfil", "Consultar mi perfil", "cookie", "200 {id,nombre,telefono,direccion}; 404", "Dato personal restringido", "id = sesión"),
    "S08": ("RF8", "P04 · guardar perfil", "Modificar mi perfil", "body: nombre?, telefono?, direccion?", "200 perfil; 400 validation_error/empty_update", "Dato personal restringido", "id = sesión"),
    "S09": ("RF8", "P04 · eliminar cuenta", "Eliminar perfil y credenciales; anonimizar pedidos", "cookie", "204; 401", "Dato personal restringido", "Solo la propia cuenta"),
    "S10": ("RF11", "P06 · enviar mensaje", "Registrar mensaje de contacto", "body: nombre, correo, mensaje 5-1000", "201 {id,status}; 400; 429", "Dato personal (correo)", "—"),
    "S11": ("RF11 RF9", "P05 · pestaña Mensajes", "Leer mensajes de contacto", "query: limit ≤50", "200 {items}; 403", "Dato personal", "Solo personal/administración"),
    "S12": ("RF3 RF4", "P01 · Confirmar y pagar", "Crear pedido y reservar stock", "header Idempotency-Key?; body: items[{product_id, qty 1-20}] (1-30 líneas), notes?",
            "201 pedido {id,status:awaiting_payment,total,items,expires_at}; 400 duplicate_items/validation; 409 insufficient_stock/product_unavailable; 503", "Dato comercial del cliente", "customer: pedido a nombre de la sesión"),
    "S13": ("RF7 RF5", "P03 pago / P04 historial", "Consultar un pedido", "ruta: order_id", "200 pedido; 404 (también si es ajeno)", "Dato comercial del cliente", "Dueño; personal/admin/auditoría ven todos (auditoría sin identidad)"),
    "S14": ("RF5", "P01/P04 · Pagar", "Abrir intención de pago por el total guardado", "ruta: order_id", "200 {order_id,payment_id,provider_ref,amount}; 409 invalid_state/order_expired; 404", "Dato comercial", "Dueño del pedido"),
    "S15": ("RF7", "P04 · Cancelar", "Cancelar un pedido pendiente y liberar stock", "ruta: order_id", "200 pedido; 409 invalid_state; 404", "Dato comercial", "Dueño; personal/admin"),
    "S16": ("RF9", "P05 · avanzar estado", "Preparar → listo → entregar", "body: status ∈ {preparing,ready,delivered}", "200 pedido; 409 invalid_transition; 403", "Dato comercial", "Personal/administración"),
    "S17": ("RF5", "P03 · cargar pago", "Consultar un pago propio", "ruta: provider_ref", "200 {payment_id,order_id,amount,currency,status}; 404", "Dato comercial", "Dueño del pago"),
    "S18": ("RF5", "P03 · Aprobar/Rechazar (sandbox)", "Simular la pantalla del proveedor", "body: outcome ∈ {approve,reject}", "200 {event_id,webhook_status}; 404; 409 invalid_state", "Dato comercial", "Dueño del pago"),
    "S19": ("RF5", "— (lo llama el proveedor)", "Recibir resultado del pago", "header X-Provider-Signature; body {event_id,type,provider_ref,amount}",
            "200 {processed|duplicate|ignored|duplicate_payment}; 401 invalid_signature; 400 amount_mismatch/validation", "Dato comercial", "Autenticada por firma, no por usuario"),
    "S20": ("RF7 RF9 RF12", "P04 · Mis pedidos / P05 · panel", "Agregar datos de varios servicios", "body: query, variables", "200 {data,errors}; errores parciales con extensions.code", "Según campo (ver Módulo 8)", "Por recurso y campo en cada servicio"),
    "S21": ("RF10", "P05 · pestaña Inventario", "Listar productos con stock", "query: categoria?, q?, limit, offset", "200 {items con stock/reservado/disponible_unidades}; 403", "Dato interno", "Personal/administración"),
    "S22": ("RF10", "P05 · Crear producto", "Agregar producto al catálogo", "body: id, categoria, emoji?, nombre, descripcion, precio>0, stock≥0", "201 producto; 409 product_exists; 400; 403", "Público tras crear", "Solo administración"),
    "S23": ("RF10", "P05 · editar producto", "Modificar nombre/descripcion/precio/activo", "body: campos opcionales", "200 producto; 400; 404; 403", "Público", "Solo administración"),
    "S24": ("RF10", "P05 · Guardar stock", "Ajustar stock físico", "body: stock 0-100000", "200 producto; 409 stock_below_reserved; 404; 403", "Dato interno", "Personal/administración"),
    "S25": ("RF13", "(API) · alta de personal", "Crear cuentas de personal, auditoría o administración", "body: email, password, role ∈ {staff,auditor,admin}", "201 {user_id,role}; 409 email_taken; 403", "Credencial", "Solo administración"),
    "S26": ("RF4", "(API) · mantenimiento", "Expirar pedidos vencidos y liberar stock", "—", "200 {expired,released_retried,commits_retried}; 403", "Dato interno", "Solo administración"),
}
ROLES = ["customer", "staff", "admin", "auditor"]
NOMBRE_ROL = {"customer": "Cliente", "staff": "Personal", "admin": "Admin.", "auditor": "Auditoría"}


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return "\n".join(out) + "\n"


def m1():
    rows = []
    for r in ROUTES:
        req, pant, prop, ent, sal, clas, cond = META[r.id]
        acceso = "anónimo" if r.auth == "none" else "autenticado (" + ", ".join(NOMBRE_ROL[x] for x in r.roles) + ")"
        verbo = {"GET": "Consultar", "POST": "Agregar/acción", "PUT": "Modificar", "DELETE": "Eliminar"}[r.method]
        rows.append([r.id, req, pant, prop, f"`{r.method} {PREFIX}{r.path}` ({verbo})", ent, sal, clas, acceso])
    (GEN / "m1-matriz-servicios.md").write_text(md_table(
        ["ID", "Requisito", "Pantalla y acción", "Propósito", "Verbo y ruta", "Entrada", "Salida y errores", "Clasificación", "Acceso"], rows), encoding="utf-8")


def m4():
    rows = []
    for r in ROUTES:
        celdas = []
        for role in ROLES:
            celdas.append("✔" if (r.auth == "none" or role in r.roles) else "403" if r.auth == "session" else "—")
        anon = "✔" if r.auth == "none" else "401"
        rows.append([r.id, f"`{r.method} {PREFIX}{r.path}`", anon] + celdas + [META[r.id][6]])
    (GEN / "m4-permisos.md").write_text(md_table(
        ["ID", "Verbo y ruta", "Anónimo"] + [NOMBRE_ROL[x] for x in ROLES] + ["Condición adicional (propiedad / campo)"], rows), encoding="utf-8")


def m6():
    rows = []
    for r in ROUTES:
        destino = f"{r.upstream}: `{r.method} {r.target}`" if r.upstream else f"orquestación en gateway (`{r.handler}`)"
        trans = "path→ruta interna; descarta cabeceras salvo " + (", ".join(r.forward) or "ninguna") + "; query permitida: " + (", ".join(r.query) or "ninguna")
        rows.append([r.id, "Gateway externo", r.method, f"`{PREFIX}{r.path}`", "anónimo" if r.auth == "none" else "sesión · " + ", ".join(NOMBRE_ROL[x] for x in r.roles),
                     destino, f"límite «{r.rate}»; cuerpo ≤ {r.body_max} B; {r.controls or 'validación en el servicio'}", r.cred or "—"])
    (GEN / "m6-rutas.md").write_text(md_table(
        ["ID", "Gateway", "Verbo", "Ruta externa", "Acceso y rol", "Sistema y ruta destino", "Controles", "Referencia de credencial"], rows), encoding="utf-8")

    rows = []
    for a, b in EDGES:
        rows.append([f"`edge/{a}__{b}`", "clave de servicio (256 bits aleatorios)", "bootstrap de Vault", f"{a} la presenta; {b} la verifica",
                     f"identificar a `{a}` ante `{b}`", f"Vault KV `secret/lr/edge/{a}__{b}`", f"solo las rutas que `{b}` permite a `{a}`",
                     f"rotar: borrar el secreto y repetir bootstrap, reiniciar {a} y {b}; revocar: borrarlo (b rechaza con 401)"])
    for s in WITH_DB:
        rows.append([f"`db/{s}`", "credencial de base de datos", "bootstrap (usuario Mongo `svc_" + s + "`)", s, f"conexión de `{s}` a su base `{s}`",
                     f"Vault KV `secret/lr/db/{s}`", f"readWrite solo sobre la base `{s}`", "rotar: repetir bootstrap (updateUser); revocar: eliminar usuario Mongo"])
    for ref, who in EXTRA.items():
        rows.append([f"`{ref}`", "secreto de firma de webhooks (HMAC-SHA256)", "bootstrap (con proveedor real: panel del proveedor)", ", ".join(who) + " (verifica y, en sandbox, firma)",
                     "autenticar eventos del proveedor de pagos", f"Vault KV `secret/lr/{ref}`", "solo `payments`; el navegador nunca lo recibe",
                     "rotar: nuevo secreto + ventana de doble verificación; revocar: eliminarlo (webhooks pasan a 401)"])
    rows.append(["`vault/token/<servicio>`", "token de Vault con política de solo lectura", "bootstrap (token raíz solo en el contenedor bootstrap)", "cada servicio, su propio token",
                 "leer únicamente sus referencias", "volumen de Docker montado solo en ese servicio (`/run/token/token`)", "política `lr-<servicio>`: capabilities=[read] sobre sus rutas",
                 "TTL 720 h; en producción AppRole/identidad de plataforma con renovación; revocar: `vault token revoke`"])
    rows.append(["`cookie lr_session`", "credencial del USUARIO (token de sesión opaco)", "Auth Service al iniciar sesión", "gateway (la valida con Auth)",
                 "sesión del navegador", "navegador: cookie HttpOnly; servidor: SHA-256 en la base de Auth", "el rol del usuario", "inactividad 30 min, absoluta 8 h; revocada al cerrar sesión o eliminar cuenta"])
    (GEN / "m6-secretos.md").write_text(md_table(
        ["Referencia", "Tipo", "Emisor", "Consumidor", "Finalidad", "Ubicación segura", "Alcance", "Rotación y revocación"], rows), encoding="utf-8")


def docstrings():
    out = {}
    for f in (ROOT / "tests").glob("test_*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
                out[(f.stem, n.name)] = (ast.get_docstring(n) or "").strip()
    return out


def resultados():
    junit = EVI / "junit.xml"
    if not junit.exists():
        return
    doc = docstrings()
    rows = []
    root = ET.parse(junit).getroot()
    total = fails = 0
    for tc in root.iter("testcase"):
        stem = tc.get("classname", "").split(".")[-1]
        name = tc.get("name")
        status = "FALLA" if tc.find("failure") is not None or tc.find("error") is not None else "OK"
        total += 1
        fails += status == "FALLA"
        d = doc.get((stem, name), "").split("\n")[0] or name.replace("test_", "", 1).replace("_", " ")
        rows.append([f"`{stem}::{name}`", d, status, f"{float(tc.get('time', 0)):.2f} s"])
    head = f"**{total - fails}/{total} pruebas OK** (fuente: `docs/evidencia/junit.xml`, generado por pytest).\n\n"
    (EVI / "resultados-pruebas.md").write_text(head + md_table(["Prueba", "Qué verifica (entrada · identidad · esperado · componente)", "Resultado", "Tiempo"], rows), encoding="utf-8")


# ---------------------------------------------------------------- trazabilidad (Módulo 10)
REQ = [
    # (id, requisito, pantalla, servicios/rutas, pruebas pytest, pruebas de navegador (prefijo), evidencia)
    ("RF1", "Ver el catálogo de productos (precios y disponibilidad vigentes)", "P01 Productos", "inventory · S01 S02",
     ["test_V1_", "test_agregacion_pedidos"], ["P01 catálogo"], "capturas/01-catalogo-1280.png, 08-catalogo-360.png"),
    ("RF2", "Filtrar por categoría / texto / disponibilidad", "P01 Productos", "inventory · S01",
     ["test_filtros_del_catalogo", "test_rutas_inexistentes"], [], "resultados-pruebas.md"),
    ("RF3", "Crear un pedido con precios y total calculados por el servidor", "P01 Productos → P03 Pago", "orders+inventory · S12",
     ["test_flujo_completo", "test_stock_insuficiente", "test_idempotency_key", "test_V6_"], ["P01 total"], "capturas/03-pago-sandbox-1280.png"),
    ("RF4", "Reservar stock sin sobreventa; liberar al cancelar o vencer", "P01 / P04", "inventory+orders · S12 S15 S26",
     ["test_concurrencia", "test_cancelar_libera", "test_expiracion_libera", "test_stock_fisico"], [], "resultados-pruebas.md"),
    ("RF5", "Pagar y confirmar por resultado firmado del proveedor (el navegador no decide «pagado»)", "P03 Pago", "payments+orders · S14 S17 S18 S19",
     ["test_flujo_completo", "test_pago_rechazado", "test_V6_"], ["P03 pantalla", "P03 pago aprobado"], "capturas/03-pago-sandbox-1280.png, 04-pago-confirmado.png"),
    ("RF6", "Crear cuenta, iniciar y cerrar sesión de forma segura", "P02 Acceso", "auth · S03 S04 S05 S06",
     ["test_registro_login", "test_login_generico", "test_csrf", "test_V2_", "test_V2b_", "test_auth_caido"], ["P02", "Cookie de sesión"], "capturas/02-modal-acceso.png"),
    ("RF7", "Consultar y cancelar mis pedidos (solo los míos)", "P04 Mis pedidos", "orders+graphql · S13 S15 S20",
     ["test_V4_", "test_agregacion_pedidos", "test_cliente_ve_solo", "test_cancelar_libera"], ["P04 Mis pedidos"], "capturas/05-mis-pedidos-1280.png"),
    ("RF8", "Ver, editar y eliminar mi perfil", "P04 Mi perfil", "clients+auth+orders · S07 S08 S09",
     ["test_eliminar_cuenta"], [], "resultados-pruebas.md"),
    ("RF9", "Personal: ver pedidos y avanzar su estado", "P05 Panel · Pedidos", "orders · S16 S20",
     ["test_flujo_completo", "test_personal_ve_clientes", "test_V3_"], ["P05"], "capturas/06-admin-pedidos-personal-1280.png"),
    ("RF10", "Administración/Personal: inventario y catálogo", "P05 Panel · Inventario", "inventory · S21 S22 S23 S24",
     ["test_panel_de_administracion", "test_V3_"], ["P05"], "capturas/06b-admin-inventario-personal-1280.png"),
    ("RF11", "Enviar un mensaje de contacto; el personal los lee", "P06 Contacto / P05", "clients · S10 S11",
     ["test_formulario_de_contacto"], [], "resultados-pruebas.md"),
    ("RF12", "Panel de operación agregado (pedidos por estado, ventas, bajo stock)", "P05 Panel", "graphql→orders+inventory · S20",
     ["test_panel_operacion", "test_limites_de_consulta", "test_limite_de_profundidad"], ["P05"], "capturas/07-admin-auditoria.png, carga.md"),
    ("RF13", "Altas de personal/auditoría solo por administración", "(API)", "auth · S25",
     ["test_V3_"], [], "resultados-pruebas.md"),
    ("RNF1", "Sin acceso directo a servicios privados; identidad y claves por arista", "—", "todos",
     ["test_V5_", "test_politica_de_minimo", "test_politicas_generadas"], [], "docs/diagramas/fronteras_confianza.png"),
    ("RNF2", "Secretos en gestor, rotables, con degradación segura", "—", "lr_common.secrets",
     ["test_lee_secreto", "test_gestor_caido"], [], "resultados-pruebas.md"),
    ("RNF3", "Registros sin credenciales ni datos personales", "—", "lr_common.logs",
     ["test_los_logs_no"], [], "resultados-pruebas.md"),
    ("RNF4", "Degradación controlada ante caídas (502/503/504, recuperación)", "—", "gateway+clientes HTTP",
     ["test_inventory_caido", "test_orders_caido"], [], "resultados-pruebas.md"),
    ("RNF5", "Desempeño: p95 dentro de objetivos con la carga proyectada", "—", "todos", [], [], "carga.md"),
]


def trazabilidad():
    import json
    junit = EVI / "junit.xml"
    if not junit.exists():
        return
    res = {}
    for tc in ET.parse(junit).getroot().iter("testcase"):
        res[tc.get("name")] = "FALLA" if (tc.find("failure") is not None or tc.find("error") is not None) else "OK"
    nav = []
    nj = EVI / "resultados-navegador.json"
    if nj.exists():
        nav = json.loads(nj.read_text(encoding="utf-8"))
    carga_ok = "cumple" in (EVI / "carga.md").read_text(encoding="utf-8") and "NO cumple" not in (EVI / "carga.md").read_text(encoding="utf-8")
    rows = []
    for rid, texto, pant, serv, pyt, nvt, evi in REQ:
        pruebas = sorted({n for n in res if any(n.startswith(p) or p in n for p in pyt)})
        navs = [x for x in nav if any(x["prueba"].startswith(p) for p in nvt)]
        okp = sum(res[n] == "OK" for n in pruebas)
        okn = sum(x["resultado"] == "OK" for x in navs)
        partes = []
        if pruebas:
            partes.append(f"{okp}/{len(pruebas)} pytest")
        if navs:
            partes.append(f"{okn}/{len(navs)} navegador")
        if rid == "RNF5":
            partes.append("objetivos de carga: " + ("cumplidos" if carga_ok else "NO cumplidos"))
        lista = "<br>".join(f"`{n}`" for n in pruebas) or "—"
        if navs:
            lista += "<br>" + "<br>".join(f"navegador: {x['prueba']}" for x in navs)
        rows.append([rid, texto, pant, serv, lista, "; ".join(partes) or "—", evi])
    (GEN / "m10-trazabilidad.md").write_text(md_table(
        ["Req.", "Requisito", "Pantalla", "Servicio · ruta", "Prueba", "Resultado", "Evidencia (docs/evidencia/)"], rows), encoding="utf-8")


def informe():
    """Ensambla docs/INFORME.md a partir de docs/modulos/*.md sustituyendo {{incluir:ruta}}."""
    import re
    partes = []
    for f in sorted((ROOT / "docs" / "modulos").glob("*.md")):
        txt = f.read_text(encoding="utf-8")
        txt = txt.replace("](../diagramas/", "](diagramas/")
        txt = re.sub(r"\{\{incluir:([^}]+)\}\}", lambda m: (ROOT / "docs" / m.group(1)).read_text(encoding="utf-8").strip(), txt)
        partes.append(txt.strip())
    (ROOT / "docs" / "INFORME.md").write_text("\n\n---\n\n".join(partes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--pruebas" in sys.argv:
        subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q", "-p", "no:cacheprovider", f"--junitxml={EVI / 'junit.xml'}"], check=False)
    m1(); m4(); m6(); resultados(); trazabilidad(); informe()
    print("generado en", GEN, "y", EVI)
