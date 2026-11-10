#!/usr/bin/env python3
"""Prueba de navegador (Playwright/Chromium) del frontend integrado con el backend real.

Uso:  python tests/browser_e2e.py        (levanta el stack local + php -S y deja capturas en docs/evidencia/capturas)
Recorre: catálogo → pedido sin sesión → registro → confirmar → pago sandbox → Mis pedidos (GraphQL)
         → panel del personal (avanzar estado) → auditoría → cliente forzando /admin.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dev_local import Stack  # noqa: E402

SHOTS = ROOT / "docs" / "evidencia" / "capturas"
SHOTS.mkdir(parents=True, exist_ok=True)
FRONT = "http://127.0.0.1:8080"
results = []


def check(name, ok, detail=""):
    results.append({"prueba": name, "resultado": "OK" if ok else "FALLA", "detalle": detail})
    print(("  ✔ " if ok else "  ✘ ") + name + (f" — {detail}" if detail and not ok else ""))


def install_cdn(ctx):
    """Si BOOTSTRAP_DIST apunta a una copia local de bootstrap/dist, se sirve en lugar del CDN (entornos sin Internet)."""
    import os
    dist = os.environ.get("BOOTSTRAP_DIST")
    if dist:
        def cdn(route):
            url = route.request.url
            if url.endswith("bootstrap.min.css"):
                route.fulfill(path=dist + "/css/bootstrap.min.css", content_type="text/css")
            elif url.endswith("bootstrap.bundle.min.js"):
                route.fulfill(path=dist + "/js/bootstrap.bundle.min.js", content_type="application/javascript")
            else:
                route.abort()
        ctx.route("**/cdn.jsdelivr.net/**", cdn)
    ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    ctx.route("**/fonts.gstatic.com/**", lambda r: r.abort())


def overflow(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def main():
    stack = Stack().start()
    php = subprocess.Popen(["php", "-S", "127.0.0.1:8080", "-t", str(ROOT / "frontend")],
                           env={**__import__("os").environ, "LR_API_BASE": stack.base},
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
            install_cdn(ctx)
            page = ctx.new_page()
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))

            # 1. catálogo real
            page.goto(f"{FRONT}/productos.php")
            page.wait_for_selector("#catalogoGrid .lr-card")
            check("P01 catálogo muestra 12 productos desde la API", page.locator("#catalogoGrid .lr-card").count() == 12)
            page.screenshot(path=str(SHOTS / "01-catalogo-1280.png"))

            # 2. pedido sin sesión → pide acceso y conserva la selección
            page.click("[data-agregar='p01']"); page.click("[data-agregar='p01']"); page.click("[data-agregar='p05']")
            check("P01 total del pedido en pantalla", page.inner_text("#pedidoTotal").replace(".", "").replace("$", "").strip().isdigit())
            page.click("#btnConfirmar")
            page.wait_for_selector("#accesoModal.show")
            check("P02 sin sesión se abre el modal de acceso", page.is_visible("#accesoModal"))
            page.screenshot(path=str(SHOTS / "02-modal-acceso.png"))

            # 3. registro real
            page.click("#tabRegistro")
            email = f"nav-{int(time.time())}@ejemplo.cl"
            page.fill("#regNombre", "Camila Prueba"); page.fill("#regEmail", email)
            page.fill("#regTelefono", "+56 9 7777 8888"); page.fill("#regPwd", "Clave-de-prueba-123")
            page.click("#panelRegistro button[type=submit]")
            page.wait_for_selector("#btnCuenta")
            check("P02 registro crea sesión (menú de cuenta visible)", page.is_visible("#btnCuenta"))
            cookies = ctx.cookies()
            ck = next(c for c in cookies if c["name"] == "lr_session")
            check("Cookie de sesión HttpOnly y no legible por JS", ck["httpOnly"] and "lr_session" not in page.evaluate("document.cookie"))

            # 4. confirmar → pago sandbox
            page.click("#btnConfirmar")
            page.wait_for_url("**/pago.php*")
            page.wait_for_selector("#pagoContenido:not(.d-none)")
            total_pantalla = page.inner_text("#pagoTotal")
            check("P03 pantalla de pago muestra total calculado por el servidor", "$" in total_pantalla)
            page.screenshot(path=str(SHOTS / "03-pago-sandbox-1280.png"), full_page=True)
            page.click("#btnAprobar")
            page.wait_for_selector("#pagoResultado .alert-success", timeout=15000)
            check("P03 pago aprobado se confirma por webhook y el pedido queda 'Pagado'", "Pagado" in page.inner_text("#pagoBadge"))
            page.screenshot(path=str(SHOTS / "04-pago-confirmado.png"), full_page=True)

            # 5. Mis pedidos (GraphQL)
            page.goto(f"{FRONT}/mis-pedidos.php")
            page.wait_for_selector("#listaPedidos [data-pedido]")
            texto = page.inner_text("#listaPedidos")
            check("P04 Mis pedidos (GraphQL) lista el pedido pagado con productos", "Pagado" in texto and "Pan de molde" in texto)
            check("P04 el perfil se carga desde clients", page.input_value("#perfNombre") == "Camila Prueba")
            page.screenshot(path=str(SHOTS / "05-mis-pedidos-1280.png"), full_page=True)

            # 6. cliente forzando el panel: la UI lo bloquea y el servidor también
            page.goto(f"{FRONT}/admin.php")
            page.wait_for_selector("#adminEstado .alert-warning")
            check("Cliente en /admin.php ve aviso y ningún dato del panel",
                  "solo para el equipo" in page.inner_text("#adminEstado") and not page.is_visible("#adminContenido"))
            r = page.evaluate("""() => fetch(document.querySelector('meta[name=lr-api-base]').content + '/api/v1/admin/products', {credentials:'include'}).then(r => r.status)""")
            check("Cliente llamando a la API de administración recibe 403", r == 403, str(r))
            page.click("#btnCuenta"); page.click("#btnSalir"); page.wait_for_url("**/index.php")

            # 7. personal avanza el estado
            def entrar(correo):
                page.goto(f"{FRONT}/admin.php")
                page.wait_for_selector("#accesoModal.show")
                page.fill("#loginEmail", correo); page.fill("#loginPwd", stack.seed_password)
                page.click("#panelLogin button[type=submit]")
                page.wait_for_selector("#adminContenido:not(.d-none)", timeout=15000)

            entrar("tienda@libreyrico.test")
            page.wait_for_selector("#tablaPedidos tbody tr[data-pedido]")
            check("P05 personal ve pedidos con nombre del cliente", "Camila" in page.inner_text("#tablaPedidos"))
            page.click("#tablaPedidos button:has-text('Iniciar preparación')")
            page.wait_for_selector("#tablaPedidos td:has-text('En preparación')")
            check("P05 personal avanza el pedido a 'En preparación'", True)
            page.screenshot(path=str(SHOTS / "06-admin-pedidos-personal-1280.png"), full_page=True)
            page.click("button:has-text('Inventario')")
            page.wait_for_selector("#tablaStock tbody tr")
            page.wait_for_timeout(500)  # fin de la transición de la pestaña
            check("P05 inventario muestra stock y reservas", page.locator("#tablaStock tbody tr").count() == 12)
            page.screenshot(path=str(SHOTS / "06b-admin-inventario-personal-1280.png"), full_page=True)
            page.click("#btnCuenta"); page.click("#btnSalir"); page.wait_for_url("**/index.php")

            # 8. auditoría: sin datos personales ni acciones
            entrar("auditoria@libreyrico.test")
            page.wait_for_selector("#tablaPedidos tbody tr[data-pedido]")
            tabla = page.inner_text("#tablaPedidos")
            check("P05 auditoría no ve nombres de clientes ni botones de acción", "Camila" not in tabla and "+56" not in tabla
                  and page.locator("#tablaPedidos button").count() == 0)
            check("P05 auditoría no ve pestañas de inventario/mensajes", not page.is_visible("button:has-text('Inventario')"))
            page.screenshot(path=str(SHOTS / "07-admin-auditoria.png"), full_page=True)

            # 9. móvil 360 px: sin desborde horizontal en las pantallas nuevas
            mctx = browser.new_context(viewport={"width": 360, "height": 740}, device_scale_factor=1)
            install_cdn(mctx)
            m = mctx.new_page()
            m.goto(f"{FRONT}/productos.php"); m.wait_for_selector("#catalogoGrid .lr-card")
            check("Móvil 360 px catálogo sin desborde horizontal", overflow(m) <= 0, str(overflow(m)))
            m.screenshot(path=str(SHOTS / "08-catalogo-360.png"))
            m.goto(f"{FRONT}/contacto.php")
            m.fill("#contactoNombre", "Visita Móvil"); m.fill("#contactoEmail", "visita@ejemplo.cl")
            m.select_option("#contactoMotivo", "pedido"); m.fill("#contactoMensaje", "Quiero cotizar una torta sin gluten.")
            m.click("#formContacto button[type=submit]")
            m.wait_for_selector("#lrToast.is-visible")
            check("Contacto envía el mensaje a la API (toast de éxito)", "Recibimos tu mensaje" in m.inner_text("#lrToast"))
            check("Móvil 360 px contacto sin desborde horizontal", overflow(m) <= 0, str(overflow(m)))
            browser.close()
    finally:
        php.terminate()
        stack.stop()
    real_errors = [e for e in errors if "fonts.g" not in e and "cdn.jsdelivr" not in e and "ERR_" not in e and "Failed to load resource" not in e]
    check("Sin errores de JavaScript en consola", not real_errors, "; ".join(real_errors[:3]))
    (ROOT / "docs" / "evidencia" / "resultados-navegador.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    failed = [r for r in results if r["resultado"] != "OK"]
    print(f"\n{len(results) - len(failed)}/{len(results)} comprobaciones OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
