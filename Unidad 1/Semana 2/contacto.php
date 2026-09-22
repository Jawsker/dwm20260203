<?php $page = 'contacto'; $titulo = 'Contacto'; include 'includes/header.php'; ?>

<div class="lr-toast" id="lrToast"></div>

<section class="lr-section">
    <div class="container">
        <div class="lr-eyebrow-line">Hablemos</div>
        <h1 class="mb-3">Contacto</h1>
        <p class="mb-5" style="max-width:60ch">
            Escríbenos para pedidos, cotizaciones de eventos o cualquier duda sobre nuestros
            productos. Respondemos dentro de 24 horas hábiles.
        </p>

        <div class="row g-5">
            <div class="col-lg-7">
                <form id="formContacto" class="lr-form" novalidate>
                    <div class="mb-3">
                        <label for="contactoNombre" class="form-label">Nombre completo</label>
                        <input type="text" class="form-control" id="contactoNombre" name="nombre" placeholder="Tu nombre">
                        <div class="invalid-feedback">Cuéntanos cómo te llamas.</div>
                    </div>
                    <div class="mb-3">
                        <label for="contactoEmail" class="form-label">Correo electrónico</label>
                        <input type="email" class="form-control" id="contactoEmail" name="email" placeholder="tucorreo@ejemplo.cl">
                        <div class="invalid-feedback">Ingresa un correo válido.</div>
                    </div>
                    <div class="mb-3">
                        <label for="contactoMotivo" class="form-label">Motivo</label>
                        <select class="form-select" id="contactoMotivo" name="motivo">
                            <option value="" selected disabled>Selecciona una opción</option>
                            <option value="pedido">Pedido personalizado</option>
                            <option value="mayorista">Venta al por mayor</option>
                            <option value="taller">Talleres</option>
                            <option value="otro">Otro</option>
                        </select>
                        <div class="invalid-feedback">Selecciona un motivo de contacto.</div>
                    </div>
                    <div class="mb-4">
                        <label for="contactoMensaje" class="form-label">Mensaje</label>
                        <textarea class="form-control" id="contactoMensaje" name="mensaje" rows="5" placeholder="Cuéntanos qué necesitas..."></textarea>
                        <div class="invalid-feedback">Escribe al menos 10 caracteres.</div>
                    </div>
                    <button type="submit" class="btn lr-btn-primary">Enviar mensaje</button>
                </form>
            </div>

            <div class="col-lg-5">
                <div class="lr-card h-100">
                    <div class="lr-card-body">
                        <h5 class="mb-3">Otras formas de contacto</h5>
                        <p class="mb-1"><strong>Dirección</strong></p>
                        <p class="text-muted">Av. Providencia 1234, Santiago</p>
                        <p class="mb-1"><strong>Horario</strong></p>
                        <p class="text-muted">Martes a sábado, 9:00 a 19:00</p>
                        <p class="mb-1"><strong>Teléfono / WhatsApp</strong></p>
                        <p class="text-muted">+56 9 1234 5678</p>
                        <p class="mb-1"><strong>Correo</strong></p>
                        <p class="text-muted mb-0">hola@libreyrico.cl</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<?php include 'includes/footer.php'; ?>
