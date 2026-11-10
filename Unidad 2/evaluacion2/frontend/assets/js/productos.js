/* ============================================================
   LIBRE & RICO — Catálogo y pedido (solo productos.php)
   Flujo: consultar catálogo (GET /products) → filtrar/buscar → agregar al pedido
          → confirmar (POST /orders) → pagar (POST /orders/{id}/pay) → pantalla de pago.

   El navegador NO envía precios ni totales: solo producto y cantidad. El servidor
   calcula el total con los precios vigentes y reserva el stock.
   Todo el contenido del catálogo y del pedido se genera con la API
   del DOM a partir de lo que responde el API Gateway; el HTML solo trae
   los contenedores vacíos. Se usa textContent (no innerHTML) para
   los datos, de modo que ningún dato del servicio se interprete
   como HTML.
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    if (!window.LR) return;
    var LR = window.LR;
    var NOMBRES_CATEGORIA = { panes: 'Panes', pasteleria: 'Pastelería', galletas: 'Galletas', salados: 'Salados' };
    var MAX_POR_LINEA = 20;

    /* ---------- Referencias al DOM ---------- */
    var grid = document.querySelector('#catalogoGrid');
    var estadoCatalogo = document.querySelector('#catalogoEstado');
    var contenedorFiltros = document.querySelector('#filtros');
    var buscador = document.querySelector('#buscador');
    var contador = document.querySelector('#contadorProductos');
    var listaPedido = document.querySelector('#pedidoLista');
    var pedidoVacio = document.querySelector('#pedidoVacio');
    var pedidoTotal = document.querySelector('#pedidoTotal');
    var pedidoCantidad = document.querySelectorAll('[data-pedido-cantidad]');
    var btnConfirmar = document.querySelector('#btnConfirmar');
    var estadoPedido = document.querySelector('#pedidoEstado');

    var formatoPesos = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

    /* ---------- Estado de la pantalla ---------- */
    var estado = {
        categorias: [],
        productos: [],
        categoria: 'todos',
        texto: '',
        pedido: {},          // id de producto → { id, nombre, precio, cantidad } (el precio es solo informativo)
        enviando: false,
        idem: null           // clave de idempotencia de este intento de pedido
    };

    /* ---------- Utilidades de DOM ---------- */
    function el(etiqueta, clases, texto) {
        var nodo = document.createElement(etiqueta);
        if (clases) nodo.className = clases;
        if (texto !== undefined) nodo.textContent = texto;
        return nodo;
    }

    function vaciar(nodo) {
        while (nodo.firstChild) nodo.removeChild(nodo.firstChild);
    }

    function quitarAcentos(texto) {
        return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    }

    /* Panel de mensajes (carga / error / vacío) reutilizable */
    function mostrarEstadoCatalogo(tipo, titulo, detalle, accion) {
        vaciar(estadoCatalogo);
        estadoCatalogo.classList.remove('d-none');
        grid.classList.add('d-none');

        var caja = el('div', 'lr-estado lr-estado--' + tipo);
        caja.setAttribute('role', tipo === 'error' ? 'alert' : 'status');

        if (tipo === 'carga') {
            var spinner = el('div', 'spinner-border lr-estado-icono');
            spinner.setAttribute('aria-hidden', 'true');
            caja.appendChild(spinner);
        } else {
            caja.appendChild(el('div', 'lr-estado-icono', tipo === 'error' ? '⚠️' : '🥣'));
        }

        var texto = el('div', 'lr-estado-texto');
        texto.appendChild(el('strong', null, titulo));
        if (detalle) texto.appendChild(el('span', null, detalle));
        caja.appendChild(texto);

        if (accion) {
            var boton = el('button', 'btn lr-btn-ghost btn-sm', accion.etiqueta);
            boton.type = 'button';
            boton.addEventListener('click', accion.alHacerClic);
            caja.appendChild(boton);
        }
        estadoCatalogo.appendChild(caja);
    }

    function ocultarEstadoCatalogo() {
        vaciar(estadoCatalogo);
        estadoCatalogo.classList.add('d-none');
        grid.classList.remove('d-none');
    }

    /* ---------- CONSULTA: cargar catálogo desde el servicio ---------- */
    function cargarCatalogo() {
        mostrarEstadoCatalogo('carga', 'Cargando el catálogo…', 'Estamos buscando lo que salió del horno.');
        contador.textContent = '';
        buscador.disabled = true;

        return LR.api.get('/products?limit=100').then(function (respuesta) {
            estado.categorias = respuesta.categorias.map(function (id) { return { id: id, nombre: NOMBRES_CATEGORIA[id] || id }; });
            estado.productos = respuesta.items;
            sincronizarPedidoConCatalogo();
            buscador.disabled = false;
            dibujarFiltros();
            dibujarCatalogo();
        }).catch(function (error) {
            estado.productos = [];
            vaciar(grid);
            dibujarFiltros();
            contador.textContent = '';
            mostrarEstadoCatalogo('error', 'No pudimos mostrar el catálogo', error.message, {
                etiqueta: 'Reintentar',
                alHacerClic: cargarCatalogo
            });
            /* Un error del catálogo no borra el pedido que el cliente ya armó */
        });
    }

    /* Si el catálogo cambió (precio/disponibilidad), el pedido muestra los valores vigentes. */
    function sincronizarPedidoConCatalogo() {
        Object.keys(estado.pedido).forEach(function (id) {
            var vigente = estado.productos.filter(function (p) { return p.id === id; })[0];
            if (!vigente || !vigente.disponible) { delete estado.pedido[id]; return; }
            estado.pedido[id].precio = vigente.precio;
            estado.pedido[id].nombre = vigente.nombre;
        });
    }

    /* ---------- Filtros generados desde los datos ---------- */
    function dibujarFiltros() {
        vaciar(contenedorFiltros);
        if (!estado.productos.length) return;

        var opciones = [{ id: 'todos', nombre: 'Todos' }].concat(estado.categorias);
        opciones.forEach(function (opcion) {
            var boton = el('button', 'btn' + (opcion.id === estado.categoria ? ' is-active' : ''), opcion.nombre);
            boton.type = 'button';
            boton.dataset.filtro = opcion.id;
            boton.setAttribute('aria-pressed', String(opcion.id === estado.categoria));
            contenedorFiltros.appendChild(boton);
        });
    }

    contenedorFiltros.addEventListener('click', function (evento) {
        var boton = evento.target.closest('[data-filtro]');
        if (!boton) return;
        estado.categoria = boton.dataset.filtro;
        contenedorFiltros.querySelectorAll('[data-filtro]').forEach(function (b) {
            var activo = b === boton;
            b.classList.toggle('is-active', activo);
            b.setAttribute('aria-pressed', String(activo));
        });
        dibujarCatalogo();
    });

    buscador.addEventListener('input', function () {
        estado.texto = buscador.value.trim();
        dibujarCatalogo();
    });

    function productosVisibles() {
        var buscado = quitarAcentos(estado.texto);
        return estado.productos.filter(function (p) {
            var coincideCategoria = estado.categoria === 'todos' || p.categoria === estado.categoria;
            var coincideTexto = !buscado || quitarAcentos(p.nombre + ' ' + p.descripcion).indexOf(buscado) !== -1;
            return coincideCategoria && coincideTexto;
        });
    }

    function nombreCategoria(id) {
        var encontrada = estado.categorias.filter(function (c) { return c.id === id; })[0];
        return encontrada ? encontrada.nombre : id;
    }

    /* ---------- Tarjetas del catálogo ---------- */
    function crearTarjeta(producto) {
        var columna = el('div', 'col');
        var tarjeta = el('article', 'lr-card');
        tarjeta.dataset.categoria = producto.categoria;

        var media = el('div', 'lr-card-media', producto.emoji);
        media.setAttribute('aria-hidden', 'true');

        var cuerpo = el('div', 'lr-card-body');
        cuerpo.appendChild(el('span', 'lr-card-cat', nombreCategoria(producto.categoria)));
        cuerpo.appendChild(el('h5', null, producto.nombre));
        cuerpo.appendChild(el('p', null, producto.descripcion));

        var pie = el('div', 'lr-card-footer');
        pie.appendChild(el('span', 'lr-price', formatoPesos.format(producto.precio)));
        var agregar = el('button', 'btn lr-btn-primary btn-sm', producto.disponible ? 'Agregar' : 'Sin stock');
        agregar.type = 'button';
        agregar.disabled = !producto.disponible;
        agregar.dataset.agregar = producto.id;
        agregar.setAttribute('aria-label', 'Agregar ' + producto.nombre + ' al pedido');
        pie.appendChild(agregar);

        tarjeta.appendChild(media);
        tarjeta.appendChild(cuerpo);
        tarjeta.appendChild(pie);
        columna.appendChild(tarjeta);
        return columna;
    }

    function dibujarCatalogo() {
        if (!estado.productos.length) {
            vaciar(grid);
            mostrarEstadoCatalogo('vacio', 'El catálogo está vacío por ahora', 'Vuelve en un rato: estamos horneando nuevos productos.');
            contador.textContent = '0 productos';
            return;
        }

        var visibles = productosVisibles();
        contador.textContent = visibles.length + (visibles.length === 1 ? ' producto' : ' productos');

        if (!visibles.length) {
            vaciar(grid);
            mostrarEstadoCatalogo('vacio', 'No encontramos productos con ese filtro', 'Prueba con otra categoría o borra la búsqueda.', {
                etiqueta: 'Limpiar filtros',
                alHacerClic: limpiarFiltros
            });
            return;
        }

        ocultarEstadoCatalogo();
        var fragmento = document.createDocumentFragment();
        visibles.forEach(function (producto) { fragmento.appendChild(crearTarjeta(producto)); });
        vaciar(grid);
        grid.appendChild(fragmento);
    }

    function limpiarFiltros() {
        estado.categoria = 'todos';
        estado.texto = '';
        buscador.value = '';
        dibujarFiltros();
        dibujarCatalogo();
    }

    /* ---------- Pedido ---------- */
    grid.addEventListener('click', function (evento) {
        var boton = evento.target.closest('[data-agregar]');
        if (!boton) return;
        agregarAlPedido(boton.dataset.agregar);
        boton.classList.add('lr-pulso');
        setTimeout(function () { boton.classList.remove('lr-pulso'); }, 350);
    });

    function agregarAlPedido(id) {
        var producto = estado.productos.filter(function (p) { return p.id === id; })[0];
        if (!producto) return;
        if (!producto.disponible) return;
        if (estado.pedido[id]) {
            estado.pedido[id].cantidad = Math.min(MAX_POR_LINEA, estado.pedido[id].cantidad + 1);
        } else {
            estado.pedido[id] = { id: id, nombre: producto.nombre, precio: producto.precio, cantidad: 1 };
        }
        estado.idem = null;
        limpiarMensajePedido();
        dibujarPedido();
    }

    listaPedido.addEventListener('click', function (evento) {
        var boton = evento.target.closest('[data-accion]');
        if (!boton) return;
        var id = boton.dataset.id;
        var item = estado.pedido[id];
        if (!item) return;

        if (boton.dataset.accion === 'mas') item.cantidad = Math.min(MAX_POR_LINEA, item.cantidad + 1);
        if (boton.dataset.accion === 'menos') item.cantidad -= 1;
        if (boton.dataset.accion === 'quitar' || item.cantidad <= 0) delete estado.pedido[id];

        estado.idem = null;
        limpiarMensajePedido();
        dibujarPedido();
    });

    function itemsDelPedido() {
        return Object.keys(estado.pedido).map(function (id) { return estado.pedido[id]; });
    }

    function crearFilaPedido(item) {
        var fila = el('li', 'lr-pedido-item');

        var info = el('div', 'lr-pedido-info');
        info.appendChild(el('span', 'lr-pedido-nombre', item.nombre));
        info.appendChild(el('span', 'lr-pedido-precio', formatoPesos.format(item.precio) + ' c/u'));

        var controles = el('div', 'lr-cantidad');
        function botonControl(accion, texto, etiqueta) {
            var b = el('button', 'lr-cantidad-btn', texto);
            b.type = 'button';
            b.dataset.accion = accion;
            b.dataset.id = item.id;
            b.setAttribute('aria-label', etiqueta + ' ' + item.nombre);
            return b;
        }
        controles.appendChild(botonControl('menos', '−', 'Quitar una unidad de'));
        controles.appendChild(el('span', 'lr-cantidad-valor', String(item.cantidad)));
        controles.appendChild(botonControl('mas', '+', 'Agregar una unidad de'));

        var subtotal = el('span', 'lr-pedido-subtotal', formatoPesos.format(item.precio * item.cantidad));
        var quitar = botonControl('quitar', '✕', 'Eliminar del pedido:');
        quitar.className = 'lr-quitar';

        fila.appendChild(info);
        fila.appendChild(controles);
        fila.appendChild(subtotal);
        fila.appendChild(quitar);
        return fila;
    }

    function dibujarPedido() {
        var items = itemsDelPedido();
        var unidades = items.reduce(function (s, i) { return s + i.cantidad; }, 0);
        var total = items.reduce(function (s, i) { return s + i.precio * i.cantidad; }, 0);

        vaciar(listaPedido);
        items.forEach(function (item) { listaPedido.appendChild(crearFilaPedido(item)); });

        pedidoVacio.classList.toggle('d-none', items.length > 0);
        listaPedido.classList.toggle('d-none', items.length === 0);
        pedidoTotal.textContent = formatoPesos.format(total);
        pedidoCantidad.forEach(function (nodo) { nodo.textContent = String(unidades); });
        btnConfirmar.disabled = items.length === 0 || estado.enviando;
    }

    /* ---------- Mensajes del pedido (carga / éxito / error) ---------- */
    function limpiarMensajePedido() {
        vaciar(estadoPedido);
    }

    function mostrarMensajePedido(clase, titulo, detalle) {
        vaciar(estadoPedido);
        var alerta = el('div', 'alert ' + clase + ' lr-alerta');
        alerta.setAttribute('role', clase === 'alert-danger' ? 'alert' : 'status');
        alerta.appendChild(el('strong', null, titulo));
        if (detalle) alerta.appendChild(el('span', null, detalle));
        estadoPedido.appendChild(alerta);
    }

    /* ---------- ACCIÓN: confirmar pedido (real) ---------- */
    function nombreDe(id) {
        var p = estado.productos.filter(function (x) { return x.id === id; })[0];
        return p ? p.nombre : id;
    }

    function textoDeError(error) {
        if (error.code === 'insufficient_stock' && error.details && error.details[0]) {
            var d = error.details[0];
            return 'No alcanza el stock de «' + nombreDe(d.product_id) + '» (quedan ' + d.disponible + '). Ajusta la cantidad e intenta de nuevo.';
        }
        if (error.code === 'product_unavailable') return 'Un producto ya no está disponible. Actualizamos el catálogo: revisa tu pedido.';
        if (error.status === 429) return 'Hiciste muchas solicitudes seguidas. Espera un minuto.';
        return error.message;
    }

    function iniciarPedido(usuario) {
        var items = itemsDelPedido();
        estado.enviando = true;
        btnConfirmar.disabled = true;
        btnConfirmar.classList.add('is-loading');
        btnConfirmar.textContent = 'Reservando tu pedido…';
        mostrarMensajePedido('alert-secondary', 'Estamos reservando tus productos', 'Esto toma unos segundos.');
        if (!estado.idem) estado.idem = LR.uuid();   // un reintento por red no duplica el pedido

        var pedidoCreado = null;
        // Se envían SOLO producto y cantidad: precio, total y estado los define el servidor.
        LR.api.post('/orders', { items: items.map(function (i) { return { product_id: i.id, qty: i.cantidad }; }) },
                    { idempotencyKey: estado.idem }).then(function (orden) {
            pedidoCreado = orden;
            return LR.api.postEmpty('/orders/' + encodeURIComponent(orden.id) + '/pay');
        }).then(function (pago) {
            estado.pedido = {}; estado.idem = null;
            window.location.href = 'pago.php?order=' + encodeURIComponent(pedidoCreado.id) + '&ref=' + encodeURIComponent(pago.provider_ref);
        }).catch(function (error) {
            if (pedidoCreado) {
                mostrarMensajePedido('alert-warning', 'Pedido ' + pedidoCreado.id + ' reservado',
                    'No pudimos abrir el pago (' + error.message + '). Lo encuentras en «Mis pedidos» y tienes unos minutos para pagarlo.');
                estado.pedido = {}; estado.idem = null;
            } else {
                mostrarMensajePedido('alert-danger', 'No pudimos confirmar tu pedido', textoDeError(error));
                if (error.code === 'insufficient_stock' || error.code === 'product_unavailable') {
                    estado.idem = null;
                    cargarCatalogo();
                }
            }
        }).then(function () {
            estado.enviando = false;
            btnConfirmar.classList.remove('is-loading');
            btnConfirmar.textContent = 'Confirmar y pagar';
            dibujarPedido();
        });
    }

    btnConfirmar.addEventListener('click', function () {
        if (!itemsDelPedido().length || estado.enviando) return;
        LR.session.ready.then(function (usuario) {
            if (!usuario) { LR.openLogin('Inicia sesión o crea tu cuenta para confirmar el pedido. Tu selección se conserva.'); return; }
            if (usuario.role !== 'customer') {
                mostrarMensajePedido('alert-warning', 'Esta cuenta no realiza pedidos', 'Las cuentas de personal y administración no compran. Usa una cuenta de cliente.');
                return;
            }
            iniciarPedido(usuario);
        });
    });

    /* ---------- Inicio ---------- */
    dibujarPedido();
    cargarCatalogo();
});
