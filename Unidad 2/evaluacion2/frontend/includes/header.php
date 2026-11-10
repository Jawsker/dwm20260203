<?php require_once __DIR__ . '/config.php'; ?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="lr-api-base" content="<?php echo htmlspecialchars($apiBase, ENT_QUOTES); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?php echo isset($titulo) ? $titulo . ' · Libre & Rico' : 'Libre & Rico · Panificados sin gluten'; ?></title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="assets/css/custom.css" rel="stylesheet">
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark lr-navbar sticky-top" id="lrNavbar">
    <div class="container">
        <a class="navbar-brand lr-brand" href="index.php">
            Libre <span class="lr-brand-amp">&amp;</span> Rico
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#lrNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="lrNav">
            <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-1">
                <li class="nav-item">
                    <a class="nav-link <?php echo ($page ?? '') === 'inicio' ? 'active' : ''; ?>" href="index.php">Inicio</a>
                </li>
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle <?php echo ($page ?? '') === 'empresa' ? 'active' : ''; ?>" href="#" role="button" data-bs-toggle="dropdown">Empresa</a>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item" href="empresa.php">Quiénes somos</a></li>
                        <li><a class="dropdown-item" href="empresa.php#mision">Misión y valores</a></li>
                        <li><a class="dropdown-item" href="empresa.php#equipo">Nuestro equipo</a></li>
                    </ul>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?php echo ($page ?? '') === 'servicios' ? 'active' : ''; ?>" href="servicios.php">Servicios</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?php echo ($page ?? '') === 'productos' ? 'active' : ''; ?>" href="productos.php">Productos</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?php echo ($page ?? '') === 'contacto' ? 'active' : ''; ?>" href="contacto.php">Contacto</a>
                </li>
                <li class="nav-item ms-lg-2 mt-2 mt-lg-0" id="cuentaArea">
                    <button type="button" class="btn lr-btn-outline btn-sm" id="btnAcceder" data-bs-toggle="modal" data-bs-target="#accesoModal">Acceder</button>
                </li>
            </ul>
        </div>
    </div>
</nav>

<!-- Modal de acceso: iniciar sesión / crear cuenta (llamadas reales al API Gateway) -->
<div class="modal fade" id="accesoModal" tabindex="-1" aria-labelledby="accesoTitulo" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content lr-modal">
            <div class="modal-header">
                <h5 class="modal-title" id="accesoTitulo">Tu cuenta</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
            </div>
            <div class="modal-body">
                <p class="small text-danger-emphasis d-none" id="accesoAviso" role="status"></p>
                <ul class="nav nav-tabs mb-3" role="tablist">
                    <li class="nav-item" role="presentation"><button class="nav-link active" id="tabLogin" data-bs-toggle="tab" data-bs-target="#panelLogin" type="button" role="tab">Ingresar</button></li>
                    <li class="nav-item" role="presentation"><button class="nav-link" id="tabRegistro" data-bs-toggle="tab" data-bs-target="#panelRegistro" type="button" role="tab">Crear cuenta</button></li>
                </ul>
                <div class="tab-content">
                    <div class="tab-pane fade show active" id="panelLogin" role="tabpanel">
                        <form id="formLogin" novalidate>
                            <div class="mb-3">
                                <label for="loginEmail" class="form-label">Correo electrónico</label>
                                <input type="email" class="form-control" id="loginEmail" name="email" autocomplete="username" required>
                            </div>
                            <div class="mb-3">
                                <label for="loginPwd" class="form-label">Contraseña</label>
                                <input type="password" class="form-control" id="loginPwd" name="password" autocomplete="current-password" required>
                            </div>
                            <div id="loginMsg" class="small mb-2" role="alert"></div>
                            <button type="submit" class="btn lr-btn-primary w-100">Ingresar</button>
                        </form>
                    </div>
                    <div class="tab-pane fade" id="panelRegistro" role="tabpanel">
                        <form id="formRegistro" novalidate>
                            <div class="mb-3">
                                <label for="regNombre" class="form-label">Nombre</label>
                                <input type="text" class="form-control" id="regNombre" maxlength="80" autocomplete="name" required>
                            </div>
                            <div class="mb-3">
                                <label for="regEmail" class="form-label">Correo electrónico</label>
                                <input type="email" class="form-control" id="regEmail" autocomplete="email" required>
                            </div>
                            <div class="mb-3">
                                <label for="regTelefono" class="form-label">Teléfono <span class="text-muted">(opcional, para coordinar el retiro)</span></label>
                                <input type="tel" class="form-control" id="regTelefono" placeholder="+56 9 1234 5678" autocomplete="tel">
                            </div>
                            <div class="mb-3">
                                <label for="regPwd" class="form-label">Contraseña <span class="text-muted">(mínimo 10 caracteres)</span></label>
                                <input type="password" class="form-control" id="regPwd" minlength="10" autocomplete="new-password" required>
                            </div>
                            <div id="regMsg" class="small mb-2" role="alert"></div>
                            <button type="submit" class="btn lr-btn-primary w-100">Crear cuenta</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
