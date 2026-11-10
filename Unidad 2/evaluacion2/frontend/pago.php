<?php
$page = 'productos';
$titulo = 'Pago';
$scripts = ['assets/js/pago.js'];
include 'includes/header.php';
?>

<section class="lr-section">
    <div class="container" style="max-width: 46rem;">
        <header class="lr-page-head">
            <div class="lr-eyebrow-line">Paso final</div>
            <h1>Pago de tu pedido</h1>
        </header>

        <div id="pagoEstado" aria-live="polite"></div>

        <div id="pagoContenido" class="d-none">
            <div class="lr-sandbox-banner" role="note">
                <strong>Entorno de prueba.</strong> Esta pantalla simula al proveedor de pagos: no se cobra dinero real.
                Tu pedido solo queda <em>pagado</em> cuando el proveedor notifica al servidor con un evento firmado;
                esta página no puede marcarlo como pagado.
            </div>

            <div class="lr-pedido mb-4">
                <div class="lr-pedido-head">
                    <h2 class="h5 mb-0">Pedido <span id="pagoNumero"></span></h2>
                    <span id="pagoBadge"></span>
                </div>
                <ul class="lr-pedido-lista" id="pagoLineas"></ul>
                <div class="lr-pedido-total"><span>Total a pagar</span><strong id="pagoTotal"></strong></div>
                <p class="small text-muted mb-0" id="pagoExpira"></p>
            </div>

            <div id="pagoAcciones" class="d-flex flex-column flex-sm-row gap-2 mb-3">
                <button type="button" class="btn lr-btn-primary flex-fill" id="btnAprobar">Aprobar pago (sandbox)</button>
                <button type="button" class="btn lr-btn-ghost flex-fill" id="btnRechazar">Rechazar pago (sandbox)</button>
            </div>
            <div id="pagoResultado" aria-live="polite"></div>
            <p class="mt-3 mb-0"><a href="mis-pedidos.php">Ir a Mis pedidos</a> · <a href="productos.php">Seguir comprando</a></p>
        </div>
    </div>
</section>

<?php include 'includes/footer.php'; ?>
