/* ============================================================
   LIBRE & RICO — eventos JS personalizados
   1. Navbar que reacciona al scroll
   2. Botón "volver arriba"
   3. Filtro de productos por categoría
   4. Validación de formulario de contacto
   5. Validación del modal de login (simulada)
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    /* ---------- 1. Navbar al hacer scroll ---------- */
    const navbar = document.getElementById('lrNavbar');
    const backTop = document.getElementById('backToTop');

    function alScrollear() {
        const scrolled = window.scrollY > 40;
        if (navbar) navbar.classList.toggle('lr-scrolled', scrolled);
        if (backTop) backTop.classList.toggle('is-visible', window.scrollY > 480);
    }
    window.addEventListener('scroll', alScrollear);
    alScrollear();

    /* ---------- 2. Botón volver arriba ---------- */
    if (backTop) {
        backTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    /* ---------- 3. Filtro de productos (solo existe en productos.php) ---------- */
    const filtros = document.querySelectorAll('[data-filtro]');
    const tarjetas = document.querySelectorAll('[data-categoria]');
    const contador = document.getElementById('contadorProductos');

    function aplicarFiltro(categoria) {
        let visibles = 0;
        tarjetas.forEach(function (tarjeta) {
            const coincide = categoria === 'todos' || tarjeta.dataset.categoria === categoria;
            tarjeta.closest('.col-6, .col-md-4, .col-lg-3').classList.toggle('lr-hidden', !coincide);
            if (coincide) visibles++;
        });
        if (contador) {
            contador.textContent = visibles + (visibles === 1 ? ' producto' : ' productos');
        }
    }

    if (filtros.length) {
        filtros.forEach(function (boton) {
            boton.addEventListener('click', function () {
                filtros.forEach(function (b) { b.classList.remove('is-active'); });
                boton.classList.add('is-active');
                aplicarFiltro(boton.dataset.filtro);
            });
        });
        aplicarFiltro('todos');
    }

    /* ---------- 4. Validación del formulario de contacto ---------- */
    const formContacto = document.getElementById('formContacto');

    if (formContacto) {
        const toast = document.getElementById('lrToast');

        formContacto.addEventListener('submit', function (evento) {
            evento.preventDefault();

            let valido = true;
            const nombre = document.getElementById('contactoNombre');
            const email = document.getElementById('contactoEmail');
            const motivo = document.getElementById('contactoMotivo');
            const mensaje = document.getElementById('contactoMensaje');

            [nombre, email, motivo, mensaje].forEach(function (campo) {
                campo.classList.remove('is-invalid');
            });

            if (!nombre.value.trim()) {
                nombre.classList.add('is-invalid');
                valido = false;
            }
            const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!regexEmail.test(email.value.trim())) {
                email.classList.add('is-invalid');
                valido = false;
            }
            if (!motivo.value) {
                motivo.classList.add('is-invalid');
                valido = false;
            }
            if (mensaje.value.trim().length < 10) {
                mensaje.classList.add('is-invalid');
                valido = false;
            }

            if (!valido) return;

            // Simulación de envío exitoso (sin backend real)
            mostrarToast(toast, '¡Gracias, ' + nombre.value.trim().split(' ')[0] + '! Recibimos tu mensaje y te responderemos pronto.');
            formContacto.reset();
        });
    }

    /* ---------- 5. Login simulado en el modal ---------- */
    const formLogin = document.getElementById('formLogin');
    if (formLogin) {
        formLogin.addEventListener('submit', function (evento) {
            evento.preventDefault();
            const email = document.getElementById('loginEmail');
            const pwd = document.getElementById('loginPwd');
            const msg = document.getElementById('loginMsg');

            let valido = true;
            [email, pwd].forEach(function (c) { c.classList.remove('is-invalid'); });

            const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!regexEmail.test(email.value.trim())) { email.classList.add('is-invalid'); valido = false; }
            if (pwd.value.length < 4) { pwd.classList.add('is-invalid'); valido = false; }

            if (!valido) {
                msg.innerHTML = '<span class="text-danger">Revisa los campos marcados.</span>';
                return;
            }
            msg.innerHTML = '<span style="color:#88432E">Sesión simulada iniciada. ¡Bienvenido/a!</span>';
        });
    }

    /* ---------- Utilidad: toast simple ---------- */
    function mostrarToast(elemento, texto) {
        if (!elemento) return;
        elemento.textContent = texto;
        elemento.classList.add('is-visible');
        clearTimeout(elemento._timeout);
        elemento._timeout = setTimeout(function () {
            elemento.classList.remove('is-visible');
        }, 4200);
    }
});
