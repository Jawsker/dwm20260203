<?php
// URL pública del API Gateway (no es un secreto). Se configura por variable de entorno; nunca se
// escriben aquí claves: el navegador solo conoce la dirección del gateway y su cookie HttpOnly.
$apiBase = rtrim(getenv('LR_API_BASE') ?: 'http://localhost:8000', '/');
