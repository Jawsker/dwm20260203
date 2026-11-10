/* ============================================================
   LIBRE & RICO — Catálogo y pedido (solo productos.php)
   Flujo: consultar catálogo → filtrar/buscar → agregar al pedido
          → confirmar pedido (acción simulada).

   Todo el contenido del catálogo y del pedido se genera con la API
   del DOM a partir de lo que responde ApiDummy; el HTML solo trae
   los contenedores vacíos. Se usa textContent (no innerHTML) para
   los datos, de modo que ningún dato del servicio se interprete
   como HTML.
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    if (!window.ApiDummy) return;

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
    var selectorModo = document.querySelector('#modoServicio');

    var formatoPesos = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

    /* ---------- Estado de la pantalla ---------- */
    var estado = {
        categorias: [],
        productos: [],
        categoria: 'todos',
        texto: '',
        pedido: {},          // id de producto → { id, nombre, precio, cantidad }
        enviando: false
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

        return window.ApiDummy.listarProductos().then(function (respuesta) {
            estado.categorias = respuesta.data.categorias;
            estado.productos = respuesta.data.productos;
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
        var agregar = el('button', 'btn lr-btn-primary btn-sm', 'Agregar');
        agregar.type = 'button';
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
        agregarAlPedido(Number(boton.dataset.agregar));
        boton.classList.add('lr-pulso');
        setTimeout(function () { boton.classList.remove('lr-pulso'); }, 350);
    });

    function agregarAlPedido(id) {
        var producto = estado.productos.filter(function (p) { return p.id === id; })[0];
        if (!producto) return;
        if (estado.pedido[id]) {
            estado.pedido[id].cantidad += 1;
        } else {
            estado.pedido[id] = { id: id, nombre: producto.nombre, precio: producto.precio, cantidad: 1 };
        }
        limpiarMensajePedido();
        dibujarPedido();
    }

    listaPedido.addEventListener('click', function (evento) {
        var boton = evento.target.closest('[data-accion]');
        if (!boton) return;
        var id = Number(boton.dataset.id);
        var item = estado.pedido[id];
        if (!item) return;

        if (boton.dataset.accion === 'mas') item.cantidad += 1;
        if (boton.dataset.accion === 'menos') item.cantidad -= 1;
        if (boton.dataset.accion === 'quitar' || item.cantidad <= 0) delete estado.pedido[id];

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

    /* ---------- ACCIÓN: confirmar pedido (simulada) ---------- */
    btnConfirmar.addEventListener('click', function () {
        var items = itemsDelPedido();
        if (!items.length || estado.enviando) return;

        estado.enviando = true;
        btnConfirmar.disabled = true;
        btnConfirmar.classList.add('is-loading');
        btnConfirmar.textContent = 'Enviando pedido…';
        mostrarMensajePedido('alert-secondary', 'Estamos registrando tu pedido', 'Esto toma unos segundos.');

        window.ApiDummy.confirmarPedido({ items: items }).then(function (respuesta) {
            estado.pedido = {};
            mostrarMensajePedido(
                'alert-success',
                '¡Pedido ' + respuesta.data.numero + ' confirmado!',
                respuesta.data.unidades + ' unidades por ' + formatoPesos.format(respuesta.data.total) + '. Retiro: ' + respuesta.data.retiro + '.'
            );
        }).catch(function (error) {
            /* El pedido se conserva para poder reintentar sin volver a armarlo */
            mostrarMensajePedido('alert-danger', 'No pudimos confirmar tu pedido', error.message + ' Tu pedido sigue guardado: puedes reintentar.');
        }).then(function () {
            estado.enviando = false;
            btnConfirmar.classList.remove('is-loading');
            btnConfirmar.textContent = 'Confirmar pedido';
            dibujarPedido();
        });
    });

    /* ---------- Panel de pruebas del servicio simulado ---------- */
    if (selectorModo) {
        selectorModo.value = window.ApiDummy.getModo();
        selectorModo.addEventListener('change', function () {
            window.ApiDummy.setModo(selectorModo.value);
            if (selectorModo.value.indexOf('catalogo') === 0 || selectorModo.value === 'normal') {
                cargarCatalogo();
            }
        });
    }

    /* ---------- Inicio ---------- */
    dibujarPedido();
    cargarCatalogo();
});
