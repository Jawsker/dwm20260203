/* ============================================================
   LIBRE & RICO — eventos JS personalizados
   1. Navbar que reacciona al scroll
   2. Botón "volver arriba"
   3. Formulario de contacto (validación + envío real a POST /contact)
   (Login/registro viven en cuenta.js; catálogo y pedido en productos.js)
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

    /* ---------- 3. Validación del formulario de contacto ---------- */
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

            var boton = formContacto.querySelector('button[type=submit]');
            if (boton) boton.disabled = true;
            var motivoTxt = motivo.options[motivo.selectedIndex].text;
            window.LR.api.post('/contact', {
                nombre: nombre.value.trim(),
                correo: email.value.trim(),
                mensaje: '[' + motivoTxt + '] ' + mensaje.value.trim()
            }).then(function () {
                mostrarToast(toast, '¡Gracias, ' + nombre.value.trim().split(' ')[0] + '! Recibimos tu mensaje y te responderemos pronto.');
                formContacto.reset();
            }).catch(function (e) {
                mostrarToast(toast, e.status === 429 ? 'Enviaste varios mensajes seguidos. Intenta de nuevo en un minuto.' : 'No pudimos enviar tu mensaje: ' + e.message);
            }).then(function () { if (boton) boton.disabled = false; });
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
