<?php $page = 'productos'; $titulo = 'Productos'; include 'includes/header.php'; ?>

<section class="lr-section" style="padding-bottom:2rem;">
    <div class="container">
        <div class="lr-eyebrow-line">Catálogo</div>
        <h1 class="mb-3">Nuestros productos</h1>
        <p class="mb-4" style="max-width:60ch">
            Todo lo que horneamos está libre de gluten y elaborado con ingredientes certificados.
            Filtra por categoría para encontrar lo que buscas.
        </p>

        <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div class="lr-filtros d-flex flex-wrap gap-2">
                <button type="button" class="btn is-active" data-filtro="todos">Todos</button>
                <button type="button" class="btn" data-filtro="panes">Panes</button>
                <button type="button" class="btn" data-filtro="pasteleria">Pastelería</button>
                <button type="button" class="btn" data-filtro="galletas">Galletas</button>
                <button type="button" class="btn" data-filtro="salados">Snacks salados</button>
            </div>
            <span class="small text-muted" id="contadorProductos"></span>
        </div>

        <div class="row g-4">

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="panes">
                    <div class="lr-card-media">🍞</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Panes</span>
                        <h5>Pan de molde</h5>
                        <p>Ideal para sándwiches, en formato de 500 g.</p>
                        <span class="lr-price">$3.190</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="panes">
                    <div class="lr-card-media">🥖</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Panes</span>
                        <h5>Baguette rústica</h5>
                        <p>Corteza crocante, miga suave. Unidad de 250 g.</p>
                        <span class="lr-price">$3.490</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="panes">
                    <div class="lr-card-media">🫓</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Panes</span>
                        <h5>Hallulla sin gluten</h5>
                        <p>Pack de 4 unidades, perfectas para el desayuno.</p>
                        <span class="lr-price">$2.990</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="pasteleria">
                    <div class="lr-card-media">🍫</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Pastelería</span>
                        <h5>Torta de chocolate</h5>
                        <p>Bizcocho húmedo con ganache. Tamaño familiar.</p>
                        <span class="lr-price">$18.990</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="pasteleria">
                    <div class="lr-card-media">🍰</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Pastelería</span>
                        <h5>Cheesecake de frutos rojos</h5>
                        <p>Base de galleta sin gluten, coulis casero.</p>
                        <span class="lr-price">$16.490</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="pasteleria">
                    <div class="lr-card-media">🧁</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Pastelería</span>
                        <h5>Brownie individual</h5>
                        <p>Intenso en cacao, con nueces opcional.</p>
                        <span class="lr-price">$1.990</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="galletas">
                    <div class="lr-card-media">🍪</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Galletas</span>
                        <h5>Avena y miel</h5>
                        <p>Bolsa de 6 unidades, avena certificada.</p>
                        <span class="lr-price">$4.290</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="galletas">
                    <div class="lr-card-media">🍫</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Galletas</span>
                        <h5>Chips de chocolate</h5>
                        <p>Bolsa de 8 unidades, crocantes por fuera.</p>
                        <span class="lr-price">$4.590</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="salados">
                    <div class="lr-card-media">🥟</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Snacks salados</span>
                        <h5>Empanaditas de queso</h5>
                        <p>Pack de 10 unidades para horno o freidora.</p>
                        <span class="lr-price">$5.990</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="salados">
                    <div class="lr-card-media">🧀</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Snacks salados</span>
                        <h5>Palitos de queso</h5>
                        <p>Crujientes, ideales para picoteo. Bolsa 150 g.</p>
                        <span class="lr-price">$3.790</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="salados">
                    <div class="lr-card-media">🥐</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Snacks salados</span>
                        <h5>Mini croissants salados</h5>
                        <p>Rellenos de jamón y queso, pack de 6.</p>
                        <span class="lr-price">$5.490</span>
                    </div>
                </div>
            </div>

            <div class="col-6 col-md-4 col-lg-3">
                <div class="lr-card" data-categoria="panes">
                    <div class="lr-card-media">🥯</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Panes</span>
                        <h5>Pan pita sin gluten</h5>
                        <p>Pack de 4, listo para rellenar.</p>
                        <span class="lr-price">$3.290</span>
                    </div>
                </div>
            </div>

        </div>
    </div>
</section>

<?php include 'includes/footer.php'; ?>
