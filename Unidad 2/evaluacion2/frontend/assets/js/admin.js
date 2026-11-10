/* ============================================================
   LIBRE & RICO — Panel de operación (personal, administración, auditoría)
   Mostrar u ocultar pestañas según el rol es solo comodidad. Cada operación vuelve a
   autorizarse en el API Gateway y en el servicio dueño: un cliente que fuerce estas llamadas recibe 403.
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';
    var LR = window.LR, el = LR.dom.el, vaciar = LR.dom.vaciar;
    var rol = null;
    var SIGUIENTE = { paid: ['preparing', 'Iniciar preparación'], preparing: ['ready', 'Marcar listo'], ready: ['delivered', 'Entregar'] };
    var estado = document.getElementById('adminEstado');
    var aviso = document.getElementById('avisoAdmin');

    var QUERY = 'query($e:String){ panelOperacion{ ventasPagadas pedidosPorEstado{ estado cantidad } productosBajoStock{ id nombre unidadesDisponibles } } ' +
        'pedidos(primeros:20, estado:$e){ total items{ id estado total creado clienteRef lineas{ nombre cantidad } cliente{ nombre telefono } } } }';

    function error(titulo, e) { vaciar(aviso); aviso.appendChild(LR.dom.alerta('alert-danger', titulo, e.message)); }

    function tarjetaResumen(titulo, valor) {
        var col = el('div', 'col-6 col-md-3');
        var c = el('div', 'lr-pedido p-3 h-100');
        c.appendChild(el('div', 'small text-muted', titulo)); c.appendChild(el('div', 'h4 mb-0', valor));
        col.appendChild(c); return col;
    }

    function cargarPedidos() {
        var filtro = document.getElementById('filtroEstado').value || null;
        return LR.api.graphql(QUERY, { e: filtro }).then(function (r) {
            var d = r.data, res = document.getElementById('resumen'); vaciar(res);
            var conteo = {}; d.panelOperacion.pedidosPorEstado.forEach(function (x) { conteo[x.estado] = x.cantidad; });
            res.appendChild(tarjetaResumen('Ventas pagadas', LR.fmt.clp(d.panelOperacion.ventasPagadas)));
            res.appendChild(tarjetaResumen('Pendientes de pago', String(conteo.awaiting_payment || 0)));
            res.appendChild(tarjetaResumen('Por preparar', String((conteo.paid || 0) + (conteo.preparing || 0))));
            var bajo = d.panelOperacion.productosBajoStock;
            res.appendChild(tarjetaResumen('Productos con poco stock', bajo === null ? 'sin acceso' : String(bajo.length)));
            vaciar(aviso);
            if (r.errors.length && rol !== 'auditor') aviso.appendChild(LR.dom.alerta('alert-warning', 'Algunos datos no pudieron cargarse', r.errors[0].message));

            var thead = document.querySelector('#tablaPedidos thead'); vaciar(thead);
            var hr = el('tr'); ['Pedido', 'Estado', rol === 'auditor' ? 'Cliente (ref.)' : 'Cliente', 'Detalle', 'Total', ''].forEach(function (h) { hr.appendChild(el('th', null, h)); });
            thead.appendChild(hr);
            var tb = document.querySelector('#tablaPedidos tbody'); vaciar(tb);
            d.pedidos.items.forEach(function (p) {
                var tr = el('tr'); tr.dataset.pedido = p.id;
                tr.appendChild(el('td', null, p.id));
                var tdE = el('td'); tdE.appendChild(LR.estadoBadge(p.estado)); tr.appendChild(tdE);
                tr.appendChild(el('td', null, rol === 'auditor' ? (p.clienteRef || '—') : (p.cliente ? p.cliente.nombre + (p.cliente.telefono ? ' · ' + p.cliente.telefono : '') : '—')));
                tr.appendChild(el('td', 'small', p.lineas.map(function (l) { return l.cantidad + '× ' + l.nombre; }).join(', ')));
                tr.appendChild(el('td', 'text-end', LR.fmt.clp(p.total)));
                var tdA = el('td');
                var sig = SIGUIENTE[p.estado];
                if (sig && (rol === 'staff' || rol === 'admin')) {
                    var b = el('button', 'btn lr-btn-primary btn-sm', sig[1]); b.type = 'button'; b.dataset.id = p.id; b.dataset.estado = sig[0]; tdA.appendChild(b);
                }
                tr.appendChild(tdA); tb.appendChild(tr);
            });
            if (!d.pedidos.items.length) { var t = el('tr'); var c = el('td', 'text-muted', 'Sin pedidos para este filtro.'); c.colSpan = 6; t.appendChild(c); tb.appendChild(t); }
        }).catch(function (e) { error('No pudimos cargar los pedidos', e); });
    }

    document.getElementById('filtroEstado').addEventListener('change', cargarPedidos);
    document.getElementById('tablaPedidos').addEventListener('click', function (ev) {
        var b = ev.target.closest('button[data-id]'); if (!b) return;
        b.disabled = true;
        LR.api.post('/admin/orders/' + encodeURIComponent(b.dataset.id) + '/status', { status: b.dataset.estado })
            .then(cargarPedidos).catch(function (e) { error('No se pudo cambiar el estado', e); b.disabled = false; });
    });

    function cargarStock() {
        return LR.api.get('/admin/products?limit=100').then(function (r) {
            var tb = document.querySelector('#tablaStock tbody'); vaciar(tb);
            r.items.forEach(function (p) {
                var tr = el('tr');
                tr.appendChild(el('td', null, (p.emoji || '') + ' ' + p.nombre));
                tr.appendChild(el('td', 'text-end', LR.fmt.clp(p.precio)));
                tr.appendChild(el('td', 'text-end', String(p.stock)));
                tr.appendChild(el('td', 'text-end', String(p.reservado)));
                tr.appendChild(el('td', 'text-end', String(p.disponible_unidades)));
                var td = el('td', 'd-flex gap-1');
                var inp = el('input', 'form-control form-control-sm lr-stock-input'); inp.type = 'number'; inp.min = '0'; inp.value = p.stock; inp.setAttribute('aria-label', 'Nuevo stock de ' + p.nombre);
                var g = el('button', 'btn lr-btn-ghost btn-sm', 'Guardar'); g.type = 'button';
                g.addEventListener('click', function () {
                    g.disabled = true;
                    LR.api.put('/admin/products/' + encodeURIComponent(p.id) + '/stock', { stock: Number(inp.value) })
                        .then(function () { return Promise.all([cargarStock(), cargarPedidos()]); }).catch(function (e) { error('No se pudo guardar el stock', e); g.disabled = false; });
                });
                td.appendChild(inp); td.appendChild(g); tr.appendChild(td); tb.appendChild(tr);
            });
        }).catch(function (e) { error('No pudimos cargar el inventario', e); });
    }

    function cargarMensajes() {
        return LR.api.get('/admin/contact?limit=20').then(function (r) {
            var ul = document.getElementById('listaMensajes'); vaciar(ul);
            if (!r.items.length) ul.appendChild(el('li', 'list-group-item text-muted', 'Sin mensajes.'));
            r.items.forEach(function (m) {
                var li = el('li', 'list-group-item');
                li.appendChild(el('strong', null, m.nombre + ' · ' + m.correo));
                li.appendChild(el('div', 'small text-muted', LR.fmt.fecha(m.created_at)));
                li.appendChild(el('div', null, m.mensaje)); ul.appendChild(li);
            });
        }).catch(function (e) { error('No pudimos cargar los mensajes', e); });
    }

    document.getElementById('formProducto').addEventListener('submit', function (ev) {
        ev.preventDefault();
        var msg = document.getElementById('npMsg'); vaciar(msg);
        LR.api.post('/admin/products', {
            id: document.getElementById('npId').value.trim(), categoria: document.getElementById('npCat').value,
            nombre: document.getElementById('npNombre').value.trim(), descripcion: document.getElementById('npDesc').value.trim(),
            precio: Number(document.getElementById('npPrecio').value), stock: Number(document.getElementById('npStock').value)
        }).then(function () { msg.appendChild(el('span', 'text-success', 'Producto creado.')); return cargarStock(); })
          .catch(function (e) { msg.appendChild(el('span', 'text-danger', e.message)); });
    });

    var NOMBRE_ROL = { staff: 'Personal de tienda: gestiona pedidos y stock.', admin: 'Administración: acceso completo, incluye catálogo y personal.', auditor: 'Auditoría: solo lectura, sin datos personales de clientes ni stock.' };
    function iniciar() {
        vaciar(estado); estado.appendChild(LR.dom.alerta('alert-secondary', 'Cargando el panel…'));
        LR.session.ready.then(function (u) {
            if (!u) { vaciar(estado); estado.appendChild(LR.dom.alerta('alert-warning', 'Inicia sesión con una cuenta del equipo')); LR.openLogin('Inicia sesión con una cuenta del equipo.'); return; }
            if (u.role === 'customer') { vaciar(estado); estado.appendChild(LR.dom.alerta('alert-warning', 'Esta sección es solo para el equipo', 'Tu cuenta de cliente puede ver sus pedidos en «Mis pedidos».')); return; }
            rol = u.role;
            document.getElementById('adminRol').textContent = NOMBRE_ROL[rol] || '';
            document.querySelectorAll('[data-solo]').forEach(function (n) { n.classList.toggle('d-none', n.dataset.solo.split(' ').indexOf(rol) === -1); });
            document.getElementById('nuevoProducto').classList.toggle('d-none', rol !== 'admin');
            vaciar(estado); document.getElementById('adminContenido').classList.remove('d-none');
            var tareas = [cargarPedidos()];
            if (rol === 'staff' || rol === 'admin') { tareas.push(cargarStock(), cargarMensajes()); }
            return Promise.all(tareas);
        });
    }
    document.addEventListener('lr:sesion', function () { window.location.reload(); });
    iniciar();
});
