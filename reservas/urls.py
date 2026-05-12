from django.urls import path

from . import views


urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("habitaciones/", views.listar_habitaciones, name="listar_habitaciones"),
    path("habitaciones/<int:habitacion_id>/", views.detalle_habitacion, name="detalle_habitacion"),
    path("habitaciones/<int:habitacion_id>/reservar/", views.crear_reserva, name="crear_reserva"),
    path("reservas/pagar/", views.pagar_reserva_cliente, name="pagar_reserva_cliente"),
    path("reserva-exitosa/<str:codigo_reserva>/", views.reserva_exitosa, name="reserva_exitosa"),

    # Área privada del cliente. El visitante navega libremente, pero debe crear
    # cuenta o iniciar sesión para confirmar una reserva y ver su historial.
    path("clientes/registro/", views.registrar_cliente, name="registrar_cliente"),
    path("clientes/panel/", views.panel_cliente, name="panel_cliente"),
    path("clientes/reservas/<str:codigo_reserva>/", views.detalle_reserva_cliente, name="detalle_reserva_cliente"),

    path("panel/", views.panel_administracion, name="panel_administracion"),

    path("panel/habitaciones/", views.panel_habitaciones, name="panel_habitaciones"),
    path("panel/habitaciones/nueva/", views.crear_habitacion, name="crear_habitacion"),
    path("panel/habitaciones/<int:habitacion_id>/editar/", views.editar_habitacion, name="editar_habitacion"),
    path("panel/habitaciones/<int:habitacion_id>/desactivar/", views.desactivar_habitacion, name="desactivar_habitacion"),
    path("panel/habitaciones/<int:habitacion_id>/imagenes/agregar/", views.agregar_imagen_habitacion, name="agregar_imagen_habitacion"),
    path("panel/imagenes/<int:imagen_id>/eliminar/", views.eliminar_imagen_habitacion, name="eliminar_imagen_habitacion"),

    path("panel/reservas/", views.panel_reservas, name="panel_reservas"),
    path("panel/reservas/<int:reserva_id>/", views.detalle_reserva_admin, name="detalle_reserva_admin"),
    path("panel/reservas/<int:reserva_id>/editar/", views.editar_reserva, name="editar_reserva"),
    path("panel/reservas/<int:reserva_id>/pago/", views.registrar_pago, name="registrar_pago"),

    path("panel/tipos/", views.panel_tipos_habitacion, name="panel_tipos_habitacion"),
    path("panel/tipos/nuevo/", views.crear_tipo_habitacion, name="crear_tipo_habitacion"),
    path("panel/tipos/<int:tipo_id>/editar/", views.editar_tipo_habitacion, name="editar_tipo_habitacion"),

    path("panel/servicios/", views.panel_servicios, name="panel_servicios"),
    path("panel/servicios/nuevo/", views.crear_servicio, name="crear_servicio"),
    path("panel/servicios/<int:servicio_id>/editar/", views.editar_servicio, name="editar_servicio"),
]
