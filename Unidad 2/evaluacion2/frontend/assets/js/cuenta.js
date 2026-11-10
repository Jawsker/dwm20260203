/* ============================================================
   LIBRE & RICO — sesión y cuenta (barra de navegación + modal de acceso)

   La pantalla pregunta al servidor quién es el usuario (GET /auth/session). Ocultar o mostrar
   enlaces según el rol es solo comodidad: la autorización real la aplican el API Gateway y los
   servicios, que responden 401/403 aunque alguien fuerce la URL o la llamada.
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';
    var LR = window.LR;
    if (!LR) return;
    var el = LR.dom.el, vaciar = LR.dom.vaciar;

    var area = document.getElementById('cuentaArea');
    var modalEl = document.getElementById('accesoModal');
    var aviso = document.getElementById('accesoAviso');
    var sesion = { user: null, email: null };
    var ultima = Promise.resolve(null);   // promesa de la última consulta de sesión

    function modal() { return window.bootstrap && modalEl ? window.bootstrap.Modal.getOrCreateInstance(modalEl) : null; }

    LR.session = {
        get user() { return sesion.user; },
        get email() { return sesion.email; },
        /* Siempre la consulta más reciente: tras iniciar sesión, `ready` ya refleja al usuario nuevo. */
        get ready() { return ultima; },
        refresh: function () {
            ultima = LR.api.get('/auth/session').then(function (s) {
                sesion.user = { id: s.user_id, role: s.role };
                sesion.email = s.email;
                return sesion.user;
            }).catch(function (e) {
                sesion.user = null; sesion.email = null;
                if (e.status && e.status !== 401) console.warn('sesión no disponible', e.code);
                return null;
            }).then(function (u) { dibujarCuenta(); return u; });
            return ultima;
        }
    };

    LR.openLogin = function (mensaje) {
        if (aviso) {
            aviso.textContent = mensaje || '';
            aviso.classList.toggle('d-none', !mensaje);
        }
        var m = modal();
        if (m) m.show();
    };

    var ROL = { customer: 'Cliente', staff: 'Personal de tienda', admin: 'Administración', auditor: 'Auditoría' };

    function dibujarCuenta() {
        if (!area) return;
        vaciar(area);
        if (!sesion.user) {
            var b = el('button', 'btn lr-btn-outline btn-sm', 'Acceder');
            b.type = 'button';
            b.id = 'btnAcceder';
            b.addEventListener('click', function () { LR.openLogin(''); });
            area.appendChild(b);
            return;
        }
        var wrap = el('div', 'dropdown');
        var toggle = el('button', 'btn lr-btn-outline btn-sm dropdown-toggle', ROL[sesion.user.role] || 'Mi cuenta');
        toggle.type = 'button';
        toggle.id = 'btnCuenta';
        toggle.setAttribute('data-bs-toggle', 'dropdown');
        toggle.setAttribute('aria-expanded', 'false');
        var menu = el('ul', 'dropdown-menu dropdown-menu-end');
        function item(texto, href) {
            var li = el('li'); var a = el('a', 'dropdown-item', texto); a.href = href; li.appendChild(a); menu.appendChild(li);
        }
        var cab = el('li'); cab.appendChild(el('span', 'dropdown-item-text small text-muted', sesion.email || '')); menu.appendChild(cab);
        if (sesion.user.role === 'customer') item('Mis pedidos y perfil', 'mis-pedidos.php');
        else item('Panel de operación', 'admin.php');
        var sep = el('li'); sep.appendChild(el('hr', 'dropdown-divider')); menu.appendChild(sep);
        var salir = el('li'); var bs = el('button', 'dropdown-item', 'Cerrar sesión'); bs.type = 'button'; bs.id = 'btnSalir';
        bs.addEventListener('click', cerrarSesion); salir.appendChild(bs); menu.appendChild(salir);
        wrap.appendChild(toggle); wrap.appendChild(menu);
        area.appendChild(wrap);
    }

    function cerrarSesion() {
        LR.api.postEmpty('/auth/logout').catch(function () { /* igual se limpia la vista */ }).then(function () {
            sesion.user = null; sesion.email = null;
            window.location.href = 'index.php';
        });
    }

    function mensaje(nodo, texto, ok) {
        vaciar(nodo);
        nodo.appendChild(el('span', ok ? 'text-success' : 'text-danger', texto));
    }

    /* ---------- Ingresar ---------- */
    var formLogin = document.getElementById('formLogin');
    if (formLogin) {
        formLogin.addEventListener('submit', function (ev) {
            ev.preventDefault();
            var msg = document.getElementById('loginMsg');
            var email = document.getElementById('loginEmail').value.trim();
            var pwd = document.getElementById('loginPwd').value;
            if (!email || !pwd) { mensaje(msg, 'Ingresa tu correo y tu contraseña.'); return; }
            var btn = formLogin.querySelector('button[type=submit]'); btn.disabled = true;
            LR.api.post('/auth/login', { email: email, password: pwd }).then(function () {
                document.getElementById('loginPwd').value = '';
                return LR.session.refresh();
            }).then(function () {
                var m = modal(); if (m) m.hide();
                document.dispatchEvent(new CustomEvent('lr:sesion', { detail: sesion.user }));
            }).catch(function (e) {
                mensaje(msg, e.status === 429 ? 'Demasiados intentos. Espera unos minutos y vuelve a probar.' : e.message);
            }).then(function () { btn.disabled = false; });
        });
    }

    /* ---------- Crear cuenta ---------- */
    var formReg = document.getElementById('formRegistro');
    if (formReg) {
        formReg.addEventListener('submit', function (ev) {
            ev.preventDefault();
            var msg = document.getElementById('regMsg');
            var datos = {
                nombre: document.getElementById('regNombre').value.trim(),
                email: document.getElementById('regEmail').value.trim(),
                password: document.getElementById('regPwd').value
            };
            var tel = document.getElementById('regTelefono').value.trim();
            if (tel) datos.telefono = tel;
            if (datos.nombre.length < 2 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(datos.email)) { mensaje(msg, 'Revisa tu nombre y tu correo.'); return; }
            if (datos.password.length < 10) { mensaje(msg, 'La contraseña debe tener al menos 10 caracteres.'); return; }
            var btn = formReg.querySelector('button[type=submit]'); btn.disabled = true;
            LR.api.post('/auth/register', datos).then(function () {
                document.getElementById('regPwd').value = '';
                return LR.session.refresh();
            }).then(function () {
                var m = modal(); if (m) m.hide();
                document.dispatchEvent(new CustomEvent('lr:sesion', { detail: sesion.user }));
            }).catch(function (e) {
                var campos = (e.details || []).map(function (d) { return d.field; }).join(', ');
                mensaje(msg, e.code === 'validation_error' && campos ? 'Revisa estos campos: ' + campos + '.' : e.message);
            }).then(function () { btn.disabled = false; });
        });
    }

    LR.session.refresh();
});
