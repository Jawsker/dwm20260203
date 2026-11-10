/* ============================================================
   LIBRE & RICO — Mis pedidos y perfil (cliente)
   Una consulta GraphQL agrega: orders (estado, montos) + inventory (emoji/precio vigente del producto)
   + clients (perfil). Si inventory no responde, el pedido se muestra igual y el producto queda sin
   detalle (error parcial). Los pedidos de otras personas nunca llegan: lo impone el servicio de pedidos.
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';
    var LR = window.LR, el = LR.dom.el, vaciar = LR.dom.vaciar;
    var PAGINA = 5;
    var pos = 0, total = 0;
    var lista = document.getElementById('listaPedidos');
    var estado = document.getElementById('pedidosEstado');
    var contenido = document.getElementById('pedidosContenido');
    var btnMas = document.getElementById('btnMas');
    var aviso = document.getElementById('avisoParcial');

    var QUERY = 'query($n:Int,$o:Int){ yo{ id rol perfil{ nombre telefono direccion } } ' +
        'pedidos(primeros:$n, desplazamiento:$o){ total items{ id estado total creado expira estadoPago requiereReembolso ' +
        'lineas{ nombre cantidad subtotal producto{ emoji disponible } } } } }';

    function tarjeta(p) {
        var c = el('article', 'lr-pedido p-3');
        c.dataset.pedido = p.id;
        var cab = el('div', 'd-flex justify-content-between align-items-start flex-wrap gap-2 mb-2');
        var t = el('div'); t.appendChild(el('strong', null, p.id)); t.appendChild(el('div', 'small text-muted', LR.fmt.fecha(p.creado)));
        cab.appendChild(t); cab.appendChild(LR.estadoBadge(p.estado));
        c.appendChild(cab);
        var ul = el('ul', 'list-unstyled mb-2');
        p.lineas.forEach(function (l) {
            var li = el('li', 'd-flex justify-content-between gap-2');
            var izq = el('span');
            izq.appendChild(el('span', null, (l.producto ? l.producto.emoji : '🥣') + ' '));
            izq.appendChild(document.createTextNode(l.cantidad + ' × ' + l.nombre));
            li.appendChild(izq); li.appendChild(el('span', null, LR.fmt.clp(l.subtotal)));
            ul.appendChild(li);
        });
        c.appendChild(ul);
        var pie = el('div', 'd-flex justify-content-between align-items-center flex-wrap gap-2');
        pie.appendChild(el('strong', null, 'Total ' + LR.fmt.clp(p.total)));
        var acc = el('div', 'd-flex gap-2');
        if (p.estado === 'awaiting_payment') {
            var pagar = el('button', 'btn lr-btn-primary btn-sm', 'Pagar'); pagar.type = 'button'; pagar.dataset.accion = 'pagar'; pagar.dataset.id = p.id;
            var cancelar = el('button', 'btn lr-btn-ghost btn-sm', 'Cancelar'); cancelar.type = 'button'; cancelar.dataset.accion = 'cancelar'; cancelar.dataset.id = p.id;
            acc.appendChild(pagar); acc.appendChild(cancelar);
        }
        pie.appendChild(acc); c.appendChild(pie);
        if (p.requiereReembolso) c.appendChild(el('p', 'small text-danger mt-2 mb-0', 'Recibimos tu pago fuera de plazo: quedó marcado para reembolso.'));
        return c;
    }

    function cargar(reiniciar) {
        if (reiniciar) { pos = 0; vaciar(lista); }
        btnMas.disabled = true;
        return LR.api.graphql(QUERY, { n: PAGINA, o: pos }).then(function (r) {
            var d = r.data;
            total = d.pedidos.total;
            vaciar(estado); contenido.classList.remove('d-none');
            if (pos === 0 && d.yo.perfil) {
                document.getElementById('perfNombre').value = d.yo.perfil.nombre || '';
                document.getElementById('perfTelefono').value = d.yo.perfil.telefono || '';
                document.getElementById('perfDireccion').value = d.yo.perfil.direccion || '';
            }
            vaciar(aviso);
            if (r.errors.length) aviso.appendChild(LR.dom.alerta('alert-warning', 'Algunos datos no pudieron cargarse', 'Mostramos tus pedidos igualmente; el detalle de producto puede faltar un momento.'));
            if (!d.pedidos.items.length && pos === 0) lista.appendChild(el('p', 'text-muted', 'Aún no tienes pedidos. ¡Arma el primero desde el catálogo!'));
            d.pedidos.items.forEach(function (p) { lista.appendChild(tarjeta(p)); });
            pos += d.pedidos.items.length;
            btnMas.classList.toggle('d-none', pos >= total);
            btnMas.disabled = false;
        });
    }

    btnMas.addEventListener('click', function () { cargar(false).catch(mostrarError); });

    lista.addEventListener('click', function (ev) {
        var b = ev.target.closest('[data-accion]');
        if (!b) return;
        b.disabled = true;
        var id = encodeURIComponent(b.dataset.id);
        var p = b.dataset.accion === 'pagar'
            ? LR.api.postEmpty('/orders/' + id + '/pay').then(function (pago) { window.location.href = 'pago.php?order=' + id + '&ref=' + encodeURIComponent(pago.provider_ref); })
            : LR.api.postEmpty('/orders/' + id + '/cancel').then(function () { return cargar(true); });
        p.catch(function (e) { b.disabled = false; vaciar(aviso); aviso.appendChild(LR.dom.alerta('alert-danger', 'No se pudo completar la acción', e.message)); cargar(true).catch(function () {}); });
    });

    document.getElementById('formPerfil').addEventListener('submit', function (ev) {
        ev.preventDefault();
        var msg = document.getElementById('perfMsg'); vaciar(msg);
        var cuerpo = {};
        var n = document.getElementById('perfNombre').value.trim(), t = document.getElementById('perfTelefono').value.trim(), d = document.getElementById('perfDireccion').value.trim();
        if (n) cuerpo.nombre = n; if (t) cuerpo.telefono = t; if (d) cuerpo.direccion = d;
        LR.api.put('/clients/me', cuerpo).then(function () { msg.appendChild(el('span', 'text-success', 'Perfil actualizado.')); })
            .catch(function (e) { msg.appendChild(el('span', 'text-danger', e.message)); });
    });

    var confirma = document.getElementById('eliminarConfirma');
    document.getElementById('btnEliminar').addEventListener('click', function () { confirma.classList.remove('d-none'); });
    document.getElementById('btnEliminarNo').addEventListener('click', function () { confirma.classList.add('d-none'); });
    document.getElementById('btnEliminarSi').addEventListener('click', function () {
        LR.api.del('/account').then(function () { window.location.href = 'index.php'; })
            .catch(function (e) { vaciar(aviso); aviso.appendChild(LR.dom.alerta('alert-danger', 'No se pudo eliminar la cuenta', e.message)); });
    });

    function mostrarError(e) {
        vaciar(estado); estado.appendChild(LR.dom.alerta('alert-danger', 'No pudimos cargar tus pedidos', e.message));
        var r = el('button', 'btn lr-btn-ghost btn-sm mt-2', 'Reintentar'); r.type = 'button';
        r.addEventListener('click', function () { iniciar(); }); estado.appendChild(r);
    }

    function iniciar() {
        vaciar(estado); estado.appendChild(LR.dom.alerta('alert-secondary', 'Cargando tus pedidos…'));
        LR.session.ready.then(function (u) {
            if (!u) { vaciar(estado); estado.appendChild(LR.dom.alerta('alert-warning', 'Inicia sesión para ver tus pedidos')); LR.openLogin('Inicia sesión para ver tus pedidos.'); return; }
            if (u.role !== 'customer') { window.location.href = 'admin.php'; return; }
            return cargar(true);
        }).catch(mostrarError);
    }
    document.addEventListener('lr:sesion', iniciar);
    iniciar();
});
