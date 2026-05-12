from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


ESTADOS_RESERVA_BLOQUEAN_DISPONIBILIDAD = ["Pendiente", "Confirmada"]


class Cliente(models.Model):
    """Persona que realiza una o varias reservas.

    El campo usuario permite que un cliente inicie sesión y consulte su historial.
    Se deja opcional para conservar compatibilidad con reservas creadas manualmente
    desde el panel administrativo.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="cliente",
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dpi = models.CharField("DPI", max_length=20, blank=True, null=True, unique=True)
    telefono = models.CharField(max_length=25)
    correo = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cliente"
        ordering = ["apellido", "nombre"]
        indexes = [
            models.Index(fields=["apellido", "nombre"], name="idx_cliente_nombre"),
            models.Index(fields=["telefono"], name="idx_cliente_telefono"),
            models.Index(fields=["correo"], name="idx_cliente_correo"),
            models.Index(fields=["usuario"], name="idx_cliente_usuario"),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class TipoHabitacion(models.Model):
    """Catálogo de tipos de habitación: individual, doble, familiar, suite, etc."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    capacidad_base = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "tipo_habitacion"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    """Catálogo de servicios que pueden ofrecer las habitaciones."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "servicio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Habitacion(models.Model):
    """Habitación o unidad reservable dentro de la posada."""

    ESTADOS = [
        ("disponible", "Disponible"),
        ("mantenimiento", "Mantenimiento"),
        ("inactiva", "Inactiva"),
    ]

    numero = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=120)
    tipo_habitacion = models.ForeignKey(
        TipoHabitacion,
        on_delete=models.PROTECT,
        related_name="habitaciones",
    )
    descripcion = models.TextField()
    capacidad_maxima = models.PositiveSmallIntegerField()
    precio_por_noche = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="disponible")
    servicios = models.ManyToManyField(
        Servicio,
        through="HabitacionServicio",
        related_name="habitaciones",
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "habitacion"
        ordering = ["numero"]
        indexes = [
            models.Index(fields=["tipo_habitacion"], name="idx_hab_tipo"),
            models.Index(fields=["estado"], name="idx_hab_estado"),
            models.Index(fields=["capacidad_maxima"], name="idx_hab_capacidad"),
            models.Index(fields=["precio_por_noche"], name="idx_hab_precio"),
        ]

    def __str__(self):
        return f"{self.numero} - {self.nombre}"

    @property
    def imagen_principal(self):
        """Retorna la imagen principal o, si no existe, la primera imagen cargada."""
        imagen = self.imagenes.filter(es_principal=True).first()
        return imagen or self.imagenes.first()


class HabitacionServicio(models.Model):
    """Tabla intermedia explícita para la relación muchos a muchos."""

    habitacion = models.ForeignKey(Habitacion, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)

    class Meta:
        db_table = "habitacion_servicio"
        constraints = [
            models.UniqueConstraint(
                fields=["habitacion", "servicio"],
                name="uq_habitacion_servicio",
            )
        ]

    def __str__(self):
        return f"{self.habitacion} - {self.servicio}"


class ImagenHabitacion(models.Model):
    """Permite registrar varias imágenes por habitación."""

    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.CASCADE,
        related_name="imagenes",
    )
    imagen = models.ImageField(upload_to="habitaciones/")
    descripcion = models.CharField(max_length=150, blank=True)
    es_principal = models.BooleanField(default=False)
    orden = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "imagen_habitacion"
        ordering = ["orden", "id"]
        indexes = [
            models.Index(fields=["habitacion", "es_principal"], name="idx_img_principal"),
        ]

    def __str__(self):
        return f"Imagen de {self.habitacion}"


class EstadoReserva(models.Model):
    """Catálogo de estados de una reserva."""

    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = "estado_reserva"
        ordering = ["id"]

    def __str__(self):
        return self.nombre


class MetodoPago(models.Model):
    """Catálogo de métodos de pago."""

    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "metodo_pago"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Reserva(models.Model):
    """Reserva realizada por un cliente para una habitación y rango de fechas."""

    codigo_reserva = models.CharField(max_length=30, unique=True, blank=True)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    estado_reserva = models.ForeignKey(
        EstadoReserva,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    fecha_entrada = models.DateField()
    fecha_salida = models.DateField()
    cantidad_personas = models.PositiveSmallIntegerField()
    total_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reserva"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["codigo_reserva"], name="idx_res_codigo"),
            models.Index(fields=["fecha_entrada"], name="idx_res_entrada"),
            models.Index(fields=["fecha_salida"], name="idx_res_salida"),
            models.Index(fields=["estado_reserva"], name="idx_res_estado"),
            models.Index(
                fields=["habitacion", "fecha_entrada", "fecha_salida"],
                name="idx_res_hab_fechas",
            ),
        ]

    def __str__(self):
        return f"{self.codigo_reserva or 'Reserva'} - {self.cliente}"

    @property
    def noches(self):
        if self.fecha_entrada and self.fecha_salida:
            return max((self.fecha_salida - self.fecha_entrada).days, 0)
        return 0

    @property
    def total_pagado(self):
        return self.pagos.aggregate(total=models.Sum("monto"))["total"] or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return self.total_estimado - self.total_pagado

    def clean(self):
        errores = {}

        if self.fecha_entrada and self.fecha_salida:
            if self.fecha_salida <= self.fecha_entrada:
                errores["fecha_salida"] = "La fecha de salida debe ser mayor que la fecha de entrada."

            if self.fecha_entrada < timezone.localdate():
                errores["fecha_entrada"] = "La fecha de entrada no puede ser una fecha pasada."

        if self.habitacion_id and self.cantidad_personas:
            if self.cantidad_personas > self.habitacion.capacidad_maxima:
                errores["cantidad_personas"] = (
                    "La cantidad de personas supera la capacidad máxima de la habitación."
                )

        if self.habitacion_id and self.fecha_entrada and self.fecha_salida and self.estado_reserva_id:
            nombre_estado = self.estado_reserva.nombre
            if nombre_estado in ESTADOS_RESERVA_BLOQUEAN_DISPONIBILIDAD:
                reservas_cruzadas = obtener_reservas_cruzadas(
                    habitacion=self.habitacion,
                    fecha_entrada=self.fecha_entrada,
                    fecha_salida=self.fecha_salida,
                ).exclude(pk=self.pk)

                if reservas_cruzadas.exists():
                    errores["habitacion"] = (
                        "La habitación ya tiene una reserva pendiente o confirmada "
                        "en el rango de fechas seleccionado."
                    )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if not self.codigo_reserva:
            self.codigo_reserva = generar_codigo_reserva()

        if self.habitacion_id and self.fecha_entrada and self.fecha_salida:
            self.total_estimado = Decimal(self.noches) * self.habitacion.precio_por_noche

        self.full_clean()
        super().save(*args, **kwargs)


class Pago(models.Model):
    """Pagos registrados para una reserva.

    monto: valor aplicado a la reserva.
    monto_recibido: dinero entregado por el cliente.
    cambio: diferencia devuelta cuando el cliente entrega más del total.
    """

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="pagos",
    )
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        related_name="pagos",
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    monto_recibido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cambio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_pago = models.DateTimeField(default=timezone.now)
    referencia = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "pago"
        ordering = ["-fecha_pago"]
        indexes = [
            models.Index(fields=["reserva"], name="idx_pago_reserva"),
            models.Index(fields=["metodo_pago"], name="idx_pago_metodo"),
            models.Index(fields=["fecha_pago"], name="idx_pago_fecha"),
        ]

    def __str__(self):
        return f"Pago {self.monto} - {self.reserva.codigo_reserva}"

    def clean(self):
        errores = {}

        if self.monto is not None and self.monto <= 0:
            errores["monto"] = "El monto del pago debe ser mayor que cero."

        if self.monto_recibido is not None and self.monto is not None:
            if self.monto_recibido < self.monto:
                errores["monto_recibido"] = "El monto recibido no puede ser menor que el monto aplicado."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.monto_recibido is not None and self.monto is not None:
            self.cambio = self.monto_recibido - self.monto
        elif self.cambio is None:
            self.cambio = Decimal("0.00")

        self.full_clean()
        super().save(*args, **kwargs)


class ComentarioHabitacion(models.Model):
    """Comentario ligado a una reserva ya registrada."""

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.PROTECT,
        related_name="comentario",
    )
    puntuacion = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentario = models.TextField()
    aprobado = models.BooleanField(default=False)
    fecha_comentario = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comentario_habitacion"
        ordering = ["-fecha_comentario"]
        indexes = [
            models.Index(fields=["aprobado"], name="idx_com_aprobado"),
            models.Index(fields=["puntuacion"], name="idx_com_puntuacion"),
        ]

    def __str__(self):
        return f"{self.puntuacion}/5 - {self.reserva.habitacion}"


def generar_codigo_reserva():
    """Genera un código legible y poco probable de repetir para identificar reservas."""
    marca_tiempo = timezone.now().strftime("%Y%m%d%H%M%S")
    sufijo = uuid4().hex[:6].upper()
    return f"RES-{marca_tiempo}-{sufijo}"


def obtener_reservas_cruzadas(habitacion, fecha_entrada, fecha_salida):
    """
    Retorna reservas que se cruzan con el rango solicitado.

    Lógica:
    Una reserva existente bloquea la habitación cuando:
    fecha_entrada_existente < nueva_fecha_salida
    y
    fecha_salida_existente > nueva_fecha_entrada
    """
    return Reserva.objects.select_related("estado_reserva").filter(
        habitacion=habitacion,
        fecha_entrada__lt=fecha_salida,
        fecha_salida__gt=fecha_entrada,
        estado_reserva__nombre__in=ESTADOS_RESERVA_BLOQUEAN_DISPONIBILIDAD,
    )


def obtener_habitaciones_disponibles(fecha_entrada=None, fecha_salida=None, personas=None):
    """
    Consulta optimizada para mostrar habitaciones disponibles.

    Usa select_related para el tipo de habitación y prefetch_related para imágenes
    y servicios, evitando consultas repetidas en las tarjetas del sitio público.
    """
    habitaciones = (
        Habitacion.objects.select_related("tipo_habitacion")
        .prefetch_related("imagenes", "servicios")
        .filter(estado="disponible")
    )

    if personas:
        habitaciones = habitaciones.filter(capacidad_maxima__gte=personas)

    if fecha_entrada and fecha_salida and fecha_salida > fecha_entrada:
        reservas_cruzadas = Reserva.objects.filter(
            fecha_entrada__lt=fecha_salida,
            fecha_salida__gt=fecha_entrada,
            estado_reserva__nombre__in=ESTADOS_RESERVA_BLOQUEAN_DISPONIBILIDAD,
        ).values_list("habitacion_id", flat=True)

        habitaciones = habitaciones.exclude(id__in=reservas_cruzadas)

    return habitaciones
