<?php
$page = 'productos';
$titulo = 'Mis pedidos';
$scripts = ['assets/js/pedidos.js'];
include 'includes/header.php';
?>

<section class="lr-section">
    <div class="container">
        <header class="lr-page-head">
            <div class="lr-eyebrow-line">Mi cuenta</div>
            <h1>Mis pedidos y perfil</h1>
            <p>Los pedidos combinan datos de dos servicios en una sola consulta (GraphQL): estado y montos del servicio de pedidos, y datos vigentes del producto desde inventario.</p>
        </header>

        <div id="pedidosEstado" aria-live="polite"></div>

        <div class="row g-4 d-none" id="pedidosContenido">
            <div class="col-12 col-lg-8">
                <h2 class="h4">Pedidos</h2>
                <div id="avisoParcial"></div>
                <div id="listaPedidos" class="d-flex flex-column gap-3"></div>
                <button type="button" class="btn lr-btn-ghost mt-3 d-none" id="btnMas">Ver más pedidos</button>
            </div>
            <aside class="col-12 col-lg-4">
                <h2 class="h4">Mi perfil</h2>
                <form id="formPerfil" class="lr-form" novalidate>
                    <div class="mb-3"><label for="perfNombre" class="form-label">Nombre</label><input class="form-control" id="perfNombre" maxlength="80"></div>
                    <div class="mb-3"><label for="perfTelefono" class="form-label">Teléfono</label><input class="form-control" id="perfTelefono" placeholder="+56 9 1234 5678"></div>
                    <div class="mb-3"><label for="perfDireccion" class="form-label">Dirección <span class="text-muted">(opcional)</span></label><input class="form-control" id="perfDireccion" maxlength="160"></div>
                    <div id="perfMsg" class="small mb-2" role="status"></div>
                    <button class="btn lr-btn-primary w-100" type="submit">Guardar cambios</button>
                </form>
                <hr>
                <h3 class="h6">Eliminar mi cuenta</h3>
                <p class="small text-muted">Borra tu perfil y tus credenciales. Tus pedidos pagados se conservan sin datos personales (registro comercial).</p>
                <button type="button" class="btn btn-outline-danger btn-sm" id="btnEliminar">Eliminar mi cuenta</button>
                <div id="eliminarConfirma" class="d-none mt-2">
                    <p class="small mb-2"><strong>¿Seguro?</strong> Esta acción no se puede deshacer.</p>
                    <button type="button" class="btn btn-danger btn-sm" id="btnEliminarSi">Sí, eliminar</button>
                    <button type="button" class="btn btn-link btn-sm" id="btnEliminarNo">Cancelar</button>
                </div>
            </aside>
        </div>
    </div>
</section>

<?php include 'includes/footer.php'; ?>
