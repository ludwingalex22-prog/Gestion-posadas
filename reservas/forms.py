from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

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
    obtener_reservas_cruzadas,
)


class EstiloFormularioMixin:
    """Agrega clases Bootstrap a los campos para evitar repetir código en cada formulario."""

    def aplicar_estilos_bootstrap(self):
        for campo in self.fields.values():
            clase_actual = campo.widget.attrs.get("class", "")
            if isinstance(campo.widget, forms.CheckboxSelectMultiple):
                continue
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs["class"] = f"{clase_actual} form-check-input".strip()
            else:
                campo.widget.attrs["class"] = f"{clase_actual} form-control".strip()


Usuario = get_user_model()


class FormularioRegistroCliente(EstiloFormularioMixin, UserCreationForm):
    """Formulario para crear una cuenta de cliente.

    Django se encarga de guardar la contraseña de forma cifrada. El sistema crea,
    además, el registro en la tabla Cliente para poder relacionar reservas e historial.
    """

    nombre = forms.CharField(max_length=100, label="Nombre")
    apellido = forms.CharField(max_length=100, label="Apellido")
    dpi = forms.CharField(max_length=20, required=False, label="DPI")
    telefono = forms.CharField(max_length=25, label="Teléfono")
    correo = forms.EmailField(label="Correo electrónico")

    class Meta:
        model = Usuario
        fields = ["username", "nombre", "apellido", "dpi", "telefono", "correo", "password1", "password2"]
        labels = {"username": "Usuario"}
        help_texts = {
            "username": "Usa un nombre corto para iniciar sesión, por ejemplo: jperez.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "Debe tener al menos 8 caracteres y no ser demasiado común."
        self.fields["password2"].help_text = "Repite la contraseña para confirmar."
        self.aplicar_estilos_bootstrap()

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()
        if Usuario.objects.filter(email__iexact=correo).exists():
            raise forms.ValidationError("Ya existe una cuenta registrada con este correo.")
        return correo

    def clean_dpi(self):
        dpi = self.cleaned_data.get("dpi", "").strip()
        if dpi and Cliente.objects.filter(dpi=dpi).exists():
            raise forms.ValidationError("Ya existe un cliente registrado con este DPI.")
        return dpi

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data["correo"]

        if commit:
            usuario.save()
            Cliente.objects.create(
                usuario=usuario,
                nombre=self.cleaned_data["nombre"],
                apellido=self.cleaned_data["apellido"],
                dpi=self.cleaned_data.get("dpi") or None,
                telefono=self.cleaned_data["telefono"],
                correo=self.cleaned_data["correo"],
            )

        return usuario


class FormularioBusquedaDisponibilidad(EstiloFormularioMixin, forms.Form):
    fecha_entrada = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha de entrada",
    )
    fecha_salida = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha de salida",
    )
    personas = forms.IntegerField(
        required=False,
        min_value=1,
        label="Personas",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_bootstrap()

    def clean(self):
        datos = super().clean()
        fecha_entrada = datos.get("fecha_entrada")
        fecha_salida = datos.get("fecha_salida")

        if fecha_entrada and fecha_entrada < timezone.localdate():
            self.add_error("fecha_entrada", "La fecha de entrada no puede ser una fecha pasada.")

        if fecha_entrada and fecha_salida and fecha_salida <= fecha_entrada:
            self.add_error("fecha_salida", "La fecha de salida debe ser mayor que la fecha de entrada.")

        return datos


class FormularioReservaCliente(EstiloFormularioMixin, forms.Form):
    """Formulario público para capturar datos del cliente antes del pago."""

    nombre = forms.CharField(max_length=100, label="Nombre")
    apellido = forms.CharField(max_length=100, label="Apellido")
    dpi = forms.CharField(max_length=20, required=False, label="DPI")
    telefono = forms.CharField(max_length=25, label="Teléfono")
    correo = forms.EmailField(required=False, label="Correo electrónico")
    fecha_entrada = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    fecha_salida = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    cantidad_personas = forms.IntegerField(min_value=1, label="Cantidad de personas")
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Observaciones",
    )

    def __init__(self, *args, habitacion=None, cliente=None, **kwargs):
        self.habitacion = habitacion
        self.cliente = cliente
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_bootstrap()

    def clean_dpi(self):
        dpi = self.cleaned_data.get("dpi", "").strip()
        if dpi:
            clientes = Cliente.objects.filter(dpi=dpi)
            if self.cliente and self.cliente.pk:
                clientes = clientes.exclude(pk=self.cliente.pk)
            if clientes.exists():
                raise forms.ValidationError("Ya existe otro cliente registrado con este DPI.")
        return dpi

    def clean(self):
        datos = super().clean()
        fecha_entrada = datos.get("fecha_entrada")
        fecha_salida = datos.get("fecha_salida")
        cantidad_personas = datos.get("cantidad_personas")

        if fecha_entrada and fecha_entrada < timezone.localdate():
            self.add_error("fecha_entrada", "La fecha de entrada no puede ser una fecha pasada.")

        if fecha_entrada and fecha_salida and fecha_salida <= fecha_entrada:
            self.add_error("fecha_salida", "La fecha de salida debe ser mayor que la fecha de entrada.")

        if self.habitacion and cantidad_personas:
            if cantidad_personas > self.habitacion.capacidad_maxima:
                self.add_error(
                    "cantidad_personas",
                    "La cantidad de personas supera la capacidad máxima de esta habitación.",
                )

        if self.habitacion and fecha_entrada and fecha_salida and fecha_salida > fecha_entrada:
            if obtener_reservas_cruzadas(self.habitacion, fecha_entrada, fecha_salida).exists():
                raise forms.ValidationError(
                    "Esta habitación ya está reservada en las fechas seleccionadas."
                )

        return datos

    def obtener_datos_para_pago(self):
        """Convierte los datos limpios en información serializable para guardarla en sesión."""
        datos = self.cleaned_data
        return {
            "habitacion_id": self.habitacion.id,
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "dpi": datos.get("dpi") or "",
            "telefono": datos["telefono"],
            "correo": datos.get("correo") or "",
            "fecha_entrada": datos["fecha_entrada"].isoformat(),
            "fecha_salida": datos["fecha_salida"].isoformat(),
            "cantidad_personas": datos["cantidad_personas"],
            "observaciones": datos.get("observaciones") or "",
        }


class FormularioPagoCliente(EstiloFormularioMixin, forms.Form):
    """Formulario público para confirmar el pago y cerrar la reserva como confirmada."""

    metodo_pago = forms.ModelChoiceField(
        queryset=MetodoPago.objects.none(),
        label="Método de pago",
    )
    monto_recibido = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Monto entregado por el cliente",
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "id": "id_monto_recibido"}),
    )
    referencia = forms.CharField(
        max_length=100,
        required=False,
        label="Referencia o número de comprobante",
    )

    def __init__(self, *args, total_reserva=Decimal("0.00"), **kwargs):
        self.total_reserva = Decimal(total_reserva)
        super().__init__(*args, **kwargs)
        self.fields["metodo_pago"].queryset = MetodoPago.objects.filter(activo=True)
        self.aplicar_estilos_bootstrap()

    def clean_monto_recibido(self):
        monto_recibido = self.cleaned_data["monto_recibido"]
        if monto_recibido < self.total_reserva:
            raise forms.ValidationError(
                "El monto entregado no puede ser menor que el total de la reserva."
            )
        return monto_recibido

    @property
    def cambio(self):
        monto_recibido = self.cleaned_data.get("monto_recibido") if hasattr(self, "cleaned_data") else None
        if monto_recibido is None:
            return Decimal("0.00")
        return monto_recibido - self.total_reserva


class FormularioHabitacion(EstiloFormularioMixin, forms.ModelForm):
    servicios = forms.ModelMultipleChoiceField(
        queryset=Servicio.objects.filter(activo=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Servicios incluidos",
    )

    class Meta:
        model = Habitacion
        fields = [
            "numero",
            "nombre",
            "tipo_habitacion",
            "descripcion",
            "capacidad_maxima",
            "precio_por_noche",
            "estado",
            "servicios",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["servicios"].initial = self.instance.servicios.all()

        self.aplicar_estilos_bootstrap()

    def save(self, commit=True):
        habitacion = super().save(commit=commit)

        if commit:
            HabitacionServicio.objects.filter(habitacion=habitacion).delete()
            for servicio in self.cleaned_data.get("servicios", []):
                HabitacionServicio.objects.create(habitacion=habitacion, servicio=servicio)

        return habitacion


class FormularioImagenHabitacion(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = ImagenHabitacion
        fields = ["imagen", "descripcion", "es_principal", "orden"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_bootstrap()


class FormularioTipoHabitacion(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = TipoHabitacion
        fields = ["nombre", "descripcion", "capacidad_base"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_bootstrap()


class FormularioServicio(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_bootstrap()


class FormularioReservaAdmin(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Reserva
        fields = [
            "cliente",
            "habitacion",
            "estado_reserva",
            "fecha_entrada",
            "fecha_salida",
            "cantidad_personas",
            "observaciones",
        ]
        widgets = {
            "fecha_entrada": forms.DateInput(attrs={"type": "date"}),
            "fecha_salida": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["habitacion"].queryset = Habitacion.objects.select_related(
            "tipo_habitacion"
        ).filter(estado__in=["disponible", "mantenimiento"])

        self.aplicar_estilos_bootstrap()


class FormularioPago(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo_pago", "monto", "monto_recibido", "referencia", "observaciones"]
        widgets = {
            "monto": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "monto_recibido": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "monto": "Monto aplicado a la reserva",
            "monto_recibido": "Monto recibido",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["metodo_pago"].queryset = MetodoPago.objects.filter(activo=True)
        self.fields["monto_recibido"].required = False
        self.aplicar_estilos_bootstrap()


class FormularioComentarioHabitacion(EstiloFormularioMixin, forms.ModelForm):
    class Meta:
        model = ComentarioHabitacion
        fields = ["puntuacion", "comentario"]
        widgets = {
            "comentario": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_bootstrap()
