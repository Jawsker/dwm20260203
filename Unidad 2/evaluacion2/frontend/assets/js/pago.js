/* ============================================================
   LIBRE & RICO — Pantalla de pago (sandbox)
   Muestra lo que dice el SERVIDOR (pedido y pago); el navegador solo elige "aprobar/rechazar"
   en la pantalla del proveedor simulado. El estado "pagado" llega luego por webhook firmado:
   aquí solo se consulta (polling) hasta que el servidor lo informe.
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';
    var LR = window.LR, el = LR.dom.el, vaciar = LR.dom.vaciar;
    var q = new URLSearchParams(window.location.search);
    var orderId = q.get('order'), ref = q.get('ref');
    var estado = document.getElementById('pagoEstado');
    var contenido = document.getElementById('pagoContenido');
    var resultado = document.getElementById('pagoResultado');
    var acciones = document.getElementById('pagoAcciones');

    function mostrar(nodo) { vaciar(estado); if (nodo) estado.appendChild(nodo); }

    if (!orderId || !ref) { mostrar(LR.dom.alerta('alert-warning', 'Falta información del pago', 'Vuelve a «Mis pedidos» y elige «Pagar».')); return; }
    mostrar(LR.dom.alerta('alert-secondary', 'Cargando tu pedido…'));

    function dibujarPedido(o) {
        document.getElementById('pagoNumero').textContent = o.id;
        var b = document.getElementById('pagoBadge'); vaciar(b); b.appendChild(LR.estadoBadge(o.status));
        var ul = document.getElementById('pagoLineas'); vaciar(ul);
        o.items.forEach(function (i) {
            var li = el('li', 'lr-pedido-item');
            var info = el('div', 'lr-pedido-info');
            info.appendChild(el('span', 'lr-pedido-nombre', i.nombre));
            info.appendChild(el('span', 'lr-pedido-precio', i.qty + ' × ' + LR.fmt.clp(i.unit_price)));
            li.appendChild(info); li.appendChild(el('span', 'lr-pedido-subtotal', LR.fmt.clp(i.subtotal)));
            ul.appendChild(li);
        });
        document.getElementById('pagoTotal').textContent = LR.fmt.clp(o.total);
        document.getElementById('pagoExpira').textContent = o.status === 'awaiting_payment' && o.expires_at
            ? 'Reserva vigente hasta ' + LR.fmt.fecha(o.expires_at) + ' (hora de tu dispositivo). Pasado ese plazo el pedido expira y el stock se libera.' : '';
    }

    function resumenFinal(o) {
        vaciar(resultado);
        var mapa = {
            paid: ['alert-success', '¡Pago confirmado!', 'Recibimos la confirmación del proveedor. Te avisaremos cuando esté listo para retirar.'],
            refund_required: ['alert-danger', 'Pago recibido fuera de plazo', 'Tu pedido había expirado; el pago quedó marcado para reembolso.'],
            expired: ['alert-warning', 'El pedido expiró', 'Arma uno nuevo desde el catálogo.'],
            cancelled: ['alert-secondary', 'Pedido cancelado', '']
        };
        var m = mapa[o.status];
        if (m) { resultado.appendChild(LR.dom.alerta(m[0], m[1], m[2])); acciones.classList.add('d-none'); }
    }

    function esperarConfirmacion(intentos) {
        return LR.api.get('/orders/' + encodeURIComponent(orderId)).then(function (o) {
            dibujarPedido(o);
            if (o.status !== 'awaiting_payment' || o.payment.status === 'failed' || intentos <= 0) return o;
            return new Promise(function (r) { setTimeout(r, 800); }).then(function () { return esperarConfirmacion(intentos - 1); });
        });
    }

    function decidir(resultadoElegido) {
        var botones = acciones.querySelectorAll('button');
        botones.forEach(function (b) { b.disabled = true; });
        vaciar(resultado);
        resultado.appendChild(LR.dom.alerta('alert-secondary', 'Esperando la confirmación del proveedor…'));
        LR.api.post('/payments/' + encodeURIComponent(ref) + '/sandbox-decision', { outcome: resultadoElegido }).then(function () {
            return esperarConfirmacion(6);
        }).then(function (o) {
            if (o.status === 'awaiting_payment' && o.payment.status === 'failed') {
                vaciar(resultado);
                resultado.appendChild(LR.dom.alerta('alert-danger', 'El pago fue rechazado', 'Tu pedido sigue reservado: vuelve a «Mis pedidos» y elige «Pagar» para reintentar antes de que expire.'));
                acciones.classList.add('d-none');
            } else { resumenFinal(o); }
        }).catch(function (e) {
            vaciar(resultado);
            resultado.appendChild(LR.dom.alerta('alert-danger', 'No pudimos completar el pago', e.message));
            botones.forEach(function (b) { b.disabled = false; });
        });
    }

    document.getElementById('btnAprobar').addEventListener('click', function () { decidir('approve'); });
    document.getElementById('btnRechazar').addEventListener('click', function () { decidir('reject'); });

    LR.session.ready.then(function (u) {
        if (!u) { mostrar(LR.dom.alerta('alert-warning', 'Inicia sesión para ver este pago')); LR.openLogin('Inicia sesión para continuar con tu pago.'); return; }
        return Promise.all([LR.api.get('/orders/' + encodeURIComponent(orderId)), LR.api.get('/payments/' + encodeURIComponent(ref))]).then(function (r) {
            var o = r[0], p = r[1];
            vaciar(estado); contenido.classList.remove('d-none');
            dibujarPedido(o);
            if (o.status !== 'awaiting_payment' || p.status !== 'pending') { resumenFinal(o); if (o.status === 'awaiting_payment') acciones.classList.add('d-none'); }
        }).catch(function (e) {
            mostrar(LR.dom.alerta('alert-danger', e.status === 404 ? 'No encontramos ese pedido' : 'No pudimos cargar el pago', e.message));
        });
    });
});
