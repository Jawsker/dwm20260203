/* ============================================================
   LIBRE & RICO — cliente del API Gateway (compartido por todas las pantallas)

   * El navegador solo habla con el API Gateway (/api/v1/...). Nunca con servicios internos.
   * La sesión viaja en una cookie HttpOnly que este código NO puede leer; por eso no hay
     tokens ni claves en JavaScript. Todas las llamadas usan credentials:'include'.
   * Precios, totales y estados que se muestran vienen del servidor; el navegador no los decide.
   * Los datos se insertan con textContent (nunca como HTML).
   ============================================================ */
(function () {
    'use strict';

    var meta = document.querySelector('meta[name="lr-api-base"]');
    var BASE = ((meta && meta.content) || 'http://localhost:8000').replace(/\/$/, '') + '/api/v1';

    function ApiError(status, code, message, correlationId, details) {
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
        this.message = message;
        this.correlationId = correlationId || null;
        this.details = details || null;
    }
    ApiError.prototype = Object.create(Error.prototype);

    function request(method, path, body, opts) {
        opts = opts || {};
        var headers = {};
        if (body !== undefined) headers['Content-Type'] = 'application/json';
        if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey;

        return fetch(BASE + path, {
            method: method,
            headers: headers,
            credentials: 'include',
            body: body !== undefined ? JSON.stringify(body) : undefined
        }).catch(function () {
            throw new ApiError(0, 'network', 'No pudimos conectar con el servidor. Revisa tu conexión e intenta de nuevo.');
        }).then(function (resp) {
            if (resp.status === 204) return null;
            return resp.json().catch(function () { return {}; }).then(function (data) {
                if (!resp.ok) {
                    var e = (data && data.error) || {};
                    throw new ApiError(resp.status, e.code || 'http_' + resp.status,
                        e.message || 'Ocurrió un error inesperado.', e.correlation_id, e.details);
                }
                return data;
            });
        });
    }

    /* GraphQL: devuelve { data, errors }. Si no hay datos en absoluto, lanza el primer error. */
    function graphql(query, variables) {
        return request('POST', '/graphql', { query: query, variables: variables || {} }).then(function (r) {
            if (r.errors && r.errors.length && !r.data) {
                var ext = r.errors[0].extensions || {};
                throw new ApiError(ext.status || 400, ext.code || 'graphql_error', r.errors[0].message);
            }
            return { data: r.data, errors: r.errors || [] };
        });
    }

    /* ---------- utilidades de DOM y formato ---------- */
    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text !== undefined && text !== null) n.textContent = text;
        return n;
    }
    function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }

    var CLP = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
    function fecha(iso) {
        if (!iso) return '';
        return new Date(iso).toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' });
    }

    var ESTADOS = {
        pending_reservation: ['Reservando stock', 'secondary'],
        awaiting_payment: ['Pendiente de pago', 'warning'],
        paid: ['Pagado', 'success'],
        preparing: ['En preparación', 'info'],
        ready: ['Listo para retiro', 'primary'],
        delivered: ['Entregado', 'dark'],
        cancelled: ['Cancelado', 'secondary'],
        expired: ['Expirado', 'secondary'],
        rejected: ['Rechazado', 'danger'],
        refund_required: ['Reembolso pendiente', 'danger']
    };
    function estadoBadge(estado) {
        var e = ESTADOS[estado] || [estado, 'secondary'];
        return el('span', 'badge text-bg-' + e[1], e[0]);
    }

    function uuid() {
        if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
        return String(Date.now()) + '-' + Math.random().toString(16).slice(2);
    }

    function alerta(clase, titulo, detalle) {
        var a = el('div', 'alert ' + clase + ' lr-alerta');
        a.setAttribute('role', clase === 'alert-danger' ? 'alert' : 'status');
        a.appendChild(el('strong', null, titulo));
        if (detalle) a.appendChild(el('span', null, detalle));
        return a;
    }

    window.LR = {
        ApiError: ApiError,
        api: {
            get: function (p) { return request('GET', p); },
            post: function (p, b, o) { return request('POST', p, b === undefined ? {} : b, o); },
            postEmpty: function (p) { return request('POST', p); },
            put: function (p, b) { return request('PUT', p, b); },
            del: function (p) { return request('DELETE', p); },
            graphql: graphql
        },
        dom: { el: el, vaciar: vaciar, alerta: alerta },
        fmt: { clp: function (n) { return CLP.format(n); }, fecha: fecha },
        estadoBadge: estadoBadge,
        uuid: uuid
    };
})();
