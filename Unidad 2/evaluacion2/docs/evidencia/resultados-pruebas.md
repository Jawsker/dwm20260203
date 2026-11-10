**37/37 pruebas OK** (fuente: `docs/evidencia/junit.xml`, generado por pytest).

| Prueba | Qué verifica (entrada · identidad · esperado · componente) | Resultado | Tiempo |
|---|---|---|---|
| `test_01_validacion_modulo7::test_V1_acceso_anonimo_al_catalogo` | V1 · entrada: GET /products · identidad: anónimo · esperado: 200 con campos de catálogo, sin stock exacto. | OK | 3.24 s |
| `test_01_validacion_modulo7::test_V2_operacion_protegida_sin_sesion` | V2 · entrada: POST /orders, GET /clients/me, POST /graphql · identidad: sin cookie · esperado: 401. | OK | 0.01 s |
| `test_01_validacion_modulo7::test_V2b_cookie_invalida_es_401` | V2b cookie invalida es 401 | OK | 0.03 s |
| `test_01_validacion_modulo7::test_V3_administracion_con_rol_sin_permiso` | V3 · entrada: operaciones de administración · identidad: customer/staff/auditor · esperado: 403. | OK | 0.51 s |
| `test_01_validacion_modulo7::test_V4_pedido_ajeno_no_devuelve_datos` | V4 · entrada: GET /orders/{id} y resumenPedido(id) · identidad: Beto sobre pedido de Ana · esperado: 404 sin datos; | OK | 0.32 s |
| `test_01_validacion_modulo7::test_V5_acceso_directo_al_backend_sin_identidad` | V5 · entrada: llamadas directas a los puertos de servicios privados · identidad: ninguna / clave falsa / cabeceras | OK | 0.15 s |
| `test_01_validacion_modulo7::test_V6_confirmar_pago_con_datos_alterados` | V6 · entrada: precio/total/estado alterados en la solicitud, endpoints de 'confirmación' inventados, webhooks falsificados, | OK | 0.38 s |
| `test_02_flujos_y_reglas::test_registro_login_logout_y_cookie_segura` | registro login logout y cookie segura | OK | 0.45 s |
| `test_02_flujos_y_reglas::test_login_generico_y_bloqueo_por_intentos` | login generico y bloqueo por intentos | OK | 6.68 s |
| `test_02_flujos_y_reglas::test_csrf_origen_y_tipo_de_contenido` | csrf origen y tipo de contenido | OK | 0.04 s |
| `test_02_flujos_y_reglas::test_rutas_inexistentes_y_verbos_no_permitidos` | rutas inexistentes y verbos no permitidos | OK | 0.02 s |
| `test_02_flujos_y_reglas::test_formulario_de_contacto_y_limite_de_solicitudes` | formulario de contacto y limite de solicitudes | OK | 0.06 s |
| `test_02_flujos_y_reglas::test_flujo_completo_pedido_pago_y_preparacion` | flujo completo pedido pago y preparacion | OK | 0.18 s |
| `test_02_flujos_y_reglas::test_pago_rechazado_conserva_pedido_y_permite_reintento` | pago rechazado conserva pedido y permite reintento | OK | 0.15 s |
| `test_02_flujos_y_reglas::test_cancelar_libera_el_stock` | cancelar libera el stock | OK | 0.07 s |
| `test_02_flujos_y_reglas::test_stock_insuficiente_y_validaciones_del_pedido` | stock insuficiente y validaciones del pedido | OK | 0.09 s |
| `test_02_flujos_y_reglas::test_concurrencia_no_se_vende_mas_de_lo_que_hay` | concurrencia no se vende mas de lo que hay | OK | 0.12 s |
| `test_02_flujos_y_reglas::test_idempotency_key_no_duplica_pedidos` | idempotency key no duplica pedidos | OK | 0.05 s |
| `test_02_flujos_y_reglas::test_expiracion_libera_stock_y_pago_tardio_requiere_reembolso` | expiracion libera stock y pago tardio requiere reembolso | OK | 6.66 s |
| `test_02_flujos_y_reglas::test_panel_de_administracion_y_productos` | panel de administracion y productos | OK | 0.30 s |
| `test_02_flujos_y_reglas::test_eliminar_cuenta_borra_perfil_y_anonimiza_pedidos` | eliminar cuenta borra perfil y anonimiza pedidos | OK | 0.44 s |
| `test_02_flujos_y_reglas::test_los_logs_no_contienen_credenciales_ni_datos_personales` | los logs no contienen credenciales ni datos personales | OK | 0.00 s |
| `test_02_flujos_y_reglas::test_filtros_del_catalogo_texto_y_disponibilidad` | RF2 · entrada: GET /products con q, categoria y available · identidad: anónimo · esperado: solo coincidencias; agotados se excluyen con available=true. | OK | 0.04 s |
| `test_02_flujos_y_reglas::test_stock_fisico_no_baja_de_lo_reservado` | RN10 · entrada: ajuste de stock menor que lo reservado · identidad: personal · esperado: 409 stock_below_reserved; igual a lo reservado, 200. | OK | 0.06 s |
| `test_03_graphql::test_agregacion_pedidos_con_productos_vigentes` | agregacion pedidos con productos vigentes | OK | 0.06 s |
| `test_03_graphql::test_cliente_ve_solo_lo_suyo_y_no_el_campo_cliente` | cliente ve solo lo suyo y no el campo cliente | OK | 0.07 s |
| `test_03_graphql::test_personal_ve_clientes_y_auditoria_no` | personal ve clientes y auditoria no | OK | 0.08 s |
| `test_03_graphql::test_panel_operacion_agrega_orders_e_inventory` | panel operacion agrega orders e inventory | OK | 0.05 s |
| `test_03_graphql::test_limites_de_consulta` | limites de consulta | OK | 0.06 s |
| `test_04_cliente_vault::test_lee_secreto_con_token_del_servicio_y_cachea` | lee secreto con token del servicio y cachea | OK | 0.52 s |
| `test_04_cliente_vault::test_politica_de_minimo_privilegio` | politica de minimo privilegio | OK | 0.52 s |
| `test_04_cliente_vault::test_gestor_caido_usa_ultimo_valor_conocido_y_luego_falla_cerrado` | gestor caido usa ultimo valor conocido y luego falla cerrado | OK | 1.24 s |
| `test_04_cliente_vault::test_politicas_generadas_por_servicio` | politicas generadas por servicio | OK | 0.00 s |
| `test_99_resiliencia::test_inventory_caido_degrada_de_forma_controlada` | inventory caido degrada de forma controlada | OK | 0.88 s |
| `test_99_resiliencia::test_orders_caido_da_503_y_se_recupera` | orders caido da 503 y se recupera | OK | 0.90 s |
| `test_99_resiliencia::test_auth_caido_falla_cerrado` | auth caido falla cerrado | OK | 1.52 s |
| `test_99_resiliencia::test_limite_de_profundidad_graphql` | El esquema actual llega a profundidad 5; se reinicia graphql con límite 3 para probar el rechazo. | OK | 2.09 s |
