/* ============================================================
   LIBRE & RICO — Servicio dummy (API simulada)
   No hay backend: el "servicio" lee un JSON servido por HTTP
   (api/productos.json) y simula latencia, éxito y fallos.

   Operaciones expuestas en window.ApiDummy:
     - listarProductos()      CONSULTA  → GET  api/productos.json
     - confirmarPedido(pedido) ACCIÓN    → POST simulado (201 / 422 / 500)
     - setModo(modo) / getModo() controla el escenario de prueba

   Modos de prueba (para demostrar los estados de la interfaz):
     normal · catalogo_lento · catalogo_error · catalogo_vacio · pedido_error
   ============================================================ */

(function (global) {
    'use strict';

    var URL_PRODUCTOS = 'api/productos.json';
    var CLAVE_MODO = 'lr_modo_servicio';
    var MODOS = ['normal', 'catalogo_lento', 'catalogo_error', 'catalogo_vacio', 'pedido_error'];

    /* Error con código HTTP simulado, para que la interfaz pueda reaccionar */
    function ApiError(status, mensaje) {
        this.name = 'ApiError';
        this.status = status;
        this.message = mensaje;
    }
    ApiError.prototype = Object.create(Error.prototype);

    function pausa(ms) {
        return new Promise(function (resolver) { setTimeout(resolver, ms); });
    }

    function latenciaAleatoria(min, max) {
        return min + Math.floor(Math.random() * (max - min + 1));
    }

    /* El modo se guarda en sessionStorage solo como comodidad; si no está disponible, usa memoria */
    var modoActual = 'normal';
    try {
        var guardado = global.sessionStorage.getItem(CLAVE_MODO);
        if (guardado && MODOS.indexOf(guardado) !== -1) modoActual = guardado;
    } catch (e) { /* almacenamiento bloqueado: se mantiene 'normal' */ }

    function setModo(modo) {
        if (MODOS.indexOf(modo) === -1) return;
        modoActual = modo;
        try { global.sessionStorage.setItem(CLAVE_MODO, modo); } catch (e) { /* sin persistencia */ }
    }

    function getModo() { return modoActual; }

    /* ---------- CONSULTA: catálogo ---------- */
    function listarProductos() {
        var espera = modoActual === 'catalogo_lento' ? 2600 : latenciaAleatoria(450, 850);

        return pausa(espera).then(function () {
            if (modoActual === 'catalogo_error') {
                throw new ApiError(503, 'El servicio de catálogo no está disponible en este momento.');
            }
            return fetch(URL_PRODUCTOS, { cache: 'no-store' });
        }).then(function (respuesta) {
            if (!respuesta.ok) {
                throw new ApiError(respuesta.status, 'El catálogo respondió con un error (' + respuesta.status + ').');
            }
            return respuesta.json();
        }).then(function (datos) {
            var productos = modoActual === 'catalogo_vacio' ? [] : datos.productos;
            return {
                status: 200,
                data: { categorias: datos.categorias, productos: productos, total: productos.length }
            };
        }).catch(function (error) {
            if (error instanceof ApiError) throw error;
            /* fetch rechaza con TypeError si no hay red o se abre el archivo sin servidor */
            throw new ApiError(0, 'No pudimos conectar con el catálogo. Revisa tu conexión e inténtalo de nuevo.');
        });
    }

    /* ---------- ACCIÓN: confirmar pedido (POST simulado) ---------- */
    function confirmarPedido(pedido) {
        return pausa(latenciaAleatoria(900, 1500)).then(function () {
            if (!pedido || !pedido.items || pedido.items.length === 0) {
                throw new ApiError(422, 'El pedido no tiene productos.');
            }
            if (modoActual === 'pedido_error') {
                throw new ApiError(500, 'No pudimos registrar tu pedido por un problema del servicio.');
            }
            var total = pedido.items.reduce(function (suma, item) {
                return suma + item.precio * item.cantidad;
            }, 0);
            return {
                status: 201,
                data: {
                    numero: 'LR-' + String(Date.now()).slice(-6),
                    total: total,
                    unidades: pedido.items.reduce(function (suma, item) { return suma + item.cantidad; }, 0),
                    retiro: 'Mañana desde las 10:00 en Av. Providencia 1234'
                }
            };
        });
    }

    global.ApiDummy = {
        listarProductos: listarProductos,
        confirmarPedido: confirmarPedido,
        setModo: setModo,
        getModo: getModo,
        MODOS: MODOS,
        ApiError: ApiError
    };
})(window);
