<?php $page = 'inicio'; $titulo = 'Inicio'; include 'includes/header.php'; ?>

<section class="lr-hero">
    <span class="lr-wheat">🌾</span>
    <div class="container position-relative">
        <div class="row align-items-center g-5">
            <div class="col-lg-7">
                <span class="lr-hero-eyebrow">100% sin gluten, horneado en Santiago</span>
                <h1>Pan de verdad, sin que el gluten se interponga</h1>
                <p class="lr-hero-lead">
                    En Libre &amp; Rico horneamos panes, tortas y galletas para quienes viven con
                    celiaquía o intolerancia al gluten, sin renunciar al sabor de lo recién hecho.
                </p>
                <div class="d-flex flex-wrap gap-3">
                    <a href="productos.php" class="btn lr-btn-primary">Ver productos</a>
                    <a href="contacto.php" class="btn lr-btn-ghost">Hacer un pedido</a>
                </div>
            </div>
            <div class="col-lg-5 d-flex justify-content-center justify-content-lg-end">
                <div class="lr-stamp">
                    SELLO<br><strong>Sin Gluten</strong>Certificado
                </div>
            </div>
        </div>
    </div>
</section>
<div class="lr-torn"></div>

<section class="lr-section">
    <div class="container">
        <div class="row g-4">
            <div class="col-md-4">
                <div class="lr-valor-icono">🌿</div>
                <h5>Ingredientes trazables</h5>
                <p>Trabajamos solo con proveedores certificados sin gluten, sin contaminación cruzada en ningún paso.</p>
            </div>
            <div class="col-md-4">
                <div class="lr-valor-icono">🔥</div>
                <h5>Horneado diario</h5>
                <p>Nada se congela por semanas: horneamos cada mañana en lotes pequeños para que llegue fresco.</p>
            </div>
            <div class="col-md-4">
                <div class="lr-valor-icono">🚲</div>
                <h5>Despacho en Santiago</h5>
                <p>Entregamos en la mayoría de las comunas del Gran Santiago dentro de 24 a 48 horas.</p>
            </div>
        </div>
    </div>
</section>

<section class="lr-section lr-section-kraft">
    <div class="container">
        <div class="lr-eyebrow-line">Lo más pedido</div>
        <h2 class="mb-4">Nuestros favoritos de la semana</h2>
        <div class="row g-4">
            <div class="col-md-4">
                <div class="lr-card">
                    <div class="lr-card-media">🥖</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Panes</span>
                        <h5>Baguette rústica</h5>
                        <p>Corteza crocante y miga suave, hecha con harina de arroz y almidón de maíz.</p>
                        <span class="lr-price">$3.490</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="lr-card">
                    <div class="lr-card-media">🍫</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Pastelería</span>
                        <h5>Torta de chocolate</h5>
                        <p>Bizcocho húmedo de cacao con ganache, ideal para cumpleaños y celebraciones.</p>
                        <span class="lr-price">$18.990</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="lr-card">
                    <div class="lr-card-media">🍪</div>
                    <div class="lr-card-body">
                        <span class="lr-card-cat">Galletas</span>
                        <h5>Galletas de avena sin gluten</h5>
                        <p>Avena certificada, miel y pasas. Vienen en bolsas de 6 unidades.</p>
                        <span class="lr-price">$4.290</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="text-center mt-5">
            <a href="productos.php" class="btn lr-btn-primary">Ver todo el catálogo</a>
        </div>
    </div>
</section>

<section class="lr-section lr-section-ink">
    <div class="container">
        <div class="row align-items-center g-5">
            <div class="col-lg-7">
                <h2>"Después del diagnóstico de mi hija, encontrar pan de verdad fue un alivio."</h2>
                <p class="mt-3" style="color:rgba(251,246,236,.78)">
                    Este es el mensaje que más recibimos, y la razón por la que existe Libre &amp; Rico:
                    que comer sin gluten no signifique renunciar a la mesa familiar.
                </p>
            </div>
            <div class="col-lg-5 text-center">
                <a href="empresa.php" class="btn lr-btn-outline">Conoce nuestra historia</a>
            </div>
        </div>
    </div>
</section>

<?php include 'includes/footer.php'; ?>
