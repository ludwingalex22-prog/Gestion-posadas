from django.contrib import admin

from .models import (
    Cliente,
    ComentarioHabitacion,
    EstadoReserva,
    Habitacion,
    HabitacionServicio,
    ImagenHabitacion,
    MetodoPago,
    Pago,
    Reserva,
    Servicio,
    TipoHabitacion,
)


class ImagenHabitacionInline(admin.TabularInline):
    model = ImagenHabitacion
    extra = 1


class HabitacionServicioInline(admin.TabularInline):
    model = HabitacionServicio
    extra = 1


@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre", "tipo_habitacion", "capacidad_maxima", "precio_por_noche", "estado")
    list_filter = ("estado", "tipo_habitacion")
    search_fields = ("numero", "nombre", "descripcion")
    inlines = [ImagenHabitacionInline, HabitacionServicioInline]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("codigo_reserva", "cliente", "habitacion", "estado_reserva", "fecha_entrada", "fecha_salida", "total_estimado")
    list_filter = ("estado_reserva", "fecha_entrada", "fecha_salida")
    search_fields = ("codigo_reserva", "cliente__nombre", "cliente__apellido", "habitacion__numero")
    autocomplete_fields = ("cliente", "habitacion")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "telefono", "correo", "usuario", "activo")
    search_fields = ("nombre", "apellido", "telefono", "correo", "dpi", "usuario__username")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("reserva", "metodo_pago", "monto", "monto_recibido", "cambio", "fecha_pago")
    list_filter = ("metodo_pago", "fecha_pago")
    search_fields = ("reserva__codigo_reserva", "referencia")


admin.site.register(TipoHabitacion)
admin.site.register(Servicio)
admin.site.register(EstadoReserva)
admin.site.register(MetodoPago)
admin.site.register(ComentarioHabitacion)
