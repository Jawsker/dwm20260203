<?php
$page = 'productos';
$titulo = 'Productos';
$scripts = ['assets/js/productos.js'];
include 'includes/header.php';
?>

<section class="lr-section lr-section-catalogo">
    <div class="container">

        <header class="lr-page-head">
            <div class="lr-eyebrow-line">Catálogo y pedido</div>
            <h1>Arma tu pedido sin gluten</h1>
            <p>
                Todo lo que horneamos está libre de gluten y elaborado con ingredientes certificados.
                Elige tus productos, ajusta las cantidades y confirma: reservamos el stock y pasas al pago para retirar en la tienda.
            </p>
        </header>

        <!-- MACROESTRUCTURA (grid de Bootstrap): catálogo 8/12 + pedido 4/12 en lg; 9/12 + 3/12 en xl; apilados bajo lg -->
        <div class="row g-4">

            <!-- Región 1: catálogo (el contenido lo genera js/productos.js con GET /api/v1/products) -->
            <div class="col-12 col-lg-8 col-xl-9">
                <div class="lr-toolbar">
                    <div class="lr-filtros" id="filtros" role="group" aria-label="Filtrar por categoría"></div>
                    <div class="lr-buscador">
                        <label for="buscador" class="visually-hidden">Buscar producto</label>
                        <input type="search" id="buscador" class="form-control" placeholder="Buscar producto…" autocomplete="off" disabled>
                    </div>
                </div>
                <p class="lr-contador" id="contadorProductos" aria-live="polite"></p>

                <div id="catalogoEstado" aria-live="polite"></div>
                <div class="row row-cols-1 row-cols-sm-2 row-cols-xl-3 g-4 d-none" id="catalogoGrid"></div>
            </div>

            <!-- Región 2: pedido en curso -->
            <aside class="col-12 col-lg-4 col-xl-3" id="pedido" aria-labelledby="tituloPedido">
                <div class="lr-pedido">
                    <div class="lr-pedido-head">
                        <h2 id="tituloPedido">Tu pedido</h2>
                        <span class="lr-badge"><span data-pedido-cantidad>0</span> u.</span>
                    </div>

                    <p class="lr-pedido-vacio" id="pedidoVacio">Aún no agregas productos. Elige algo del catálogo para empezar.</p>
                    <ul class="lr-pedido-lista d-none" id="pedidoLista"></ul>

                    <div class="lr-pedido-total">
                        <span>Total</span>
                        <strong id="pedidoTotal">$0</strong>
                    </div>

                    <div id="pedidoEstado" aria-live="polite"></div>

                    <button type="button" class="btn lr-btn-primary w-100" id="btnConfirmar" disabled>Confirmar y pagar</button>
                </div>
            </aside>
        </div>

    </div>
</section>

<a href="#pedido" class="lr-fab d-lg-none">Ver pedido (<span data-pedido-cantidad>0</span>)</a>

<?php include 'includes/footer.php'; ?>
