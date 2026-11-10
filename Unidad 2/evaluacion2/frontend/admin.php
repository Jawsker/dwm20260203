<?php
$page = 'productos';
$titulo = 'Panel de operación';
$scripts = ['assets/js/admin.js'];
include 'includes/header.php';
?>

<section class="lr-section">
    <div class="container">
        <header class="lr-page-head">
            <div class="lr-eyebrow-line">Operación</div>
            <h1>Panel de la tienda</h1>
            <p id="adminRol">Cargando tu rol…</p>
        </header>

        <div id="adminEstado" aria-live="polite"></div>

        <div class="d-none" id="adminContenido">
            <div class="row g-3 mb-4" id="resumen"></div>
            <div id="avisoAdmin"></div>

            <ul class="nav nav-tabs mb-3" role="tablist">
                <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tabPedidos" type="button">Pedidos</button></li>
                <li class="nav-item" data-solo="staff admin"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabInventario" type="button">Inventario</button></li>
                <li class="nav-item" data-solo="staff admin"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabMensajes" type="button">Mensajes</button></li>
            </ul>

            <div class="tab-content">
                <div class="tab-pane fade show active" id="tabPedidos">
                    <div class="d-flex gap-2 mb-3 align-items-center flex-wrap">
                        <label for="filtroEstado" class="form-label mb-0">Estado</label>
                        <select id="filtroEstado" class="form-select w-auto">
                            <option value="">Todos</option>
                            <option value="awaiting_payment">Pendiente de pago</option>
                            <option value="paid">Pagado</option>
                            <option value="preparing">En preparación</option>
                            <option value="ready">Listo para retiro</option>
                            <option value="delivered">Entregado</option>
                            <option value="expired">Expirado</option>
                            <option value="refund_required">Reembolso pendiente</option>
                        </select>
                    </div>
                    <div class="lr-table-wrap"><table class="table table-sm align-middle" id="tablaPedidos"><thead></thead><tbody></tbody></table></div>
                </div>

                <div class="tab-pane fade" id="tabInventario">
                    <div class="lr-table-wrap"><table class="table table-sm align-middle" id="tablaStock">
                        <thead><tr><th>Producto</th><th class="text-end">Precio</th><th class="text-end">Stock</th><th class="text-end">Reservado</th><th class="text-end">Disponible</th><th>Nuevo stock</th></tr></thead>
                        <tbody></tbody></table></div>
                    <details class="mt-3 d-none" id="nuevoProducto">
                        <summary>Crear producto (solo administración)</summary>
                        <form id="formProducto" class="lr-form row g-2 mt-2" novalidate>
                            <div class="col-6 col-md-3"><label class="form-label" for="npId">Id</label><input class="form-control" id="npId" placeholder="pan-integral"></div>
                            <div class="col-6 col-md-3"><label class="form-label" for="npCat">Categoría</label>
                                <select class="form-select" id="npCat"><option>panes</option><option>pasteleria</option><option>galletas</option><option>salados</option></select></div>
                            <div class="col-12 col-md-6"><label class="form-label" for="npNombre">Nombre</label><input class="form-control" id="npNombre"></div>
                            <div class="col-12"><label class="form-label" for="npDesc">Descripción</label><input class="form-control" id="npDesc"></div>
                            <div class="col-6 col-md-3"><label class="form-label" for="npPrecio">Precio (CLP)</label><input class="form-control" id="npPrecio" type="number" min="1"></div>
                            <div class="col-6 col-md-3"><label class="form-label" for="npStock">Stock inicial</label><input class="form-control" id="npStock" type="number" min="0" value="10"></div>
                            <div class="col-12"><button class="btn lr-btn-primary" type="submit">Crear producto</button> <span id="npMsg" class="small ms-2" role="status"></span></div>
                        </form>
                    </details>
                </div>

                <div class="tab-pane fade" id="tabMensajes"><ul class="list-group" id="listaMensajes"></ul></div>
            </div>
        </div>
    </div>
</section>

<?php include 'includes/footer.php'; ?>
