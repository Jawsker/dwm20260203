<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
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
                <li class="nav-item ms-lg-2 mt-2 mt-lg-0">
                    <button type="button" class="btn lr-btn-outline btn-sm" data-bs-toggle="modal" data-bs-target="#accesoModal">Acceder</button>
                </li>
            </ul>
        </div>
    </div>
</nav>

<!-- Modal de acceso -->
<div class="modal fade" id="accesoModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content lr-modal">
            <div class="modal-header">
                <h5 class="modal-title">Ingresa a tu cuenta</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="formLogin" novalidate>
                    <div class="mb-3">
                        <label for="loginEmail" class="form-label">Correo electrónico</label>
                        <input type="email" class="form-control" id="loginEmail" name="email" placeholder="tucorreo@ejemplo.cl" required>
                        <div class="invalid-feedback">Ingresa un correo válido.</div>
                    </div>
                    <div class="mb-3">
                        <label for="loginPwd" class="form-label">Contraseña</label>
                        <input type="password" class="form-control" id="loginPwd" name="password" placeholder="Tu contraseña" required minlength="4">
                        <div class="invalid-feedback">La contraseña debe tener al menos 4 caracteres.</div>
                    </div>
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" id="recordarme">
                        <label class="form-check-label" for="recordarme">Recordarme</label>
                    </div>
                    <div id="loginMsg" class="small mb-2"></div>
                    <button type="submit" class="btn lr-btn-primary w-100">Ingresar</button>
                </form>
            </div>
        </div>
    </div>
</div>
