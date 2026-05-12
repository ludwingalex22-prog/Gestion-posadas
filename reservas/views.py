from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login as iniciar_sesion_usuario
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    FormularioBusquedaDisponibilidad,
    FormularioHabitacion,
    FormularioImagenHabitacion,
    FormularioPago,
    FormularioPagoCliente,
    FormularioRegistroCliente,
    FormularioReservaAdmin,
    FormularioReservaCliente,
    FormularioServicio,
    FormularioTipoHabitacion,
)
from .models import (
    Cliente,
    ComentarioHabitacion,
    EstadoReserva,
    Habitacion,
    ImagenHabitacion,
    Pago,
    Reserva,
    Servicio,
    TipoHabitacion,
    obtener_habitaciones_disponibles,
    obtener_reservas_cruzadas,
)


CLAVE_RESERVA_EN_SESION = "datos_reserva_cliente"


def usuario_es_administrador(usuario):
    """Permite entrar al panel solo a usuarios autenticados con permiso de staff."""
    return usuario.is_authenticated and usuario.is_staff


def url_segura(request, destino):
    """Evita redirecciones externas no autorizadas al usar el parámetro next."""
    if not destino:
        return None
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return destino
    return None


def obtener_perfil_cliente(usuario):
    """Obtiene el perfil de cliente ligado al usuario autenticado."""
    if not usuario.is_authenticated or usuario.is_staff:
        return None
    try:
        return usuario.cliente
    except Cliente.DoesNotExist:
        return None


def convertir_fecha(texto_fecha):
    """Convierte una fecha guardada en sesión a objeto date."""
    return date.fromisoformat(texto_fecha)


def calcular_total_reserva(habitacion, fecha_entrada, fecha_salida):
    """Calcula noches y total de una reserva según las fechas elegidas."""
    noches = max((fecha_salida - fecha_entrada).days, 0)
    total = Decimal(noches) * habitacion.precio_por_noche
    return noches, total


def crear_o_actualizar_cliente(datos_reserva, usuario=None):
    """Crea o actualiza el cliente que quedará asociado a la reserva.

    Si la reserva la hace un usuario cliente autenticado, siempre se usa su propio
    perfil. Así se evita que una reserva termine asociada por error a otra cuenta
    solo porque alguien escribió un DPI o correo repetido.
    """
    dpi = datos_reserva.get("dpi") or None
    correo = datos_reserva.get("correo") or None

    if usuario and usuario.is_authenticated and not usuario.is_staff:
        cliente = obtener_perfil_cliente(usuario)
        if cliente is None:
            cliente = Cliente(usuario=usuario)

        cliente.nombre = datos_reserva["nombre"]
        cliente.apellido = datos_reserva["apellido"]
        cliente.dpi = dpi
        cliente.telefono = datos_reserva["telefono"]
        cliente.correo = correo or usuario.email
        cliente.save()
        return cliente

    cliente = None
    if dpi:
        cliente, _ = Cliente.objects.get_or_create(
            dpi=dpi,
            defaults={
                "nombre": datos_reserva["nombre"],
                "apellido": datos_reserva["apellido"],
                "telefono": datos_reserva["telefono"],
                "correo": correo,
            },
        )
    elif correo:
        cliente = Cliente.objects.filter(correo=correo).first()

    if cliente is None:
        cliente = Cliente.objects.create(
            nombre=datos_reserva["nombre"],
            apellido=datos_reserva["apellido"],
            dpi=dpi,
            telefono=datos_reserva["telefono"],
            correo=correo,
        )
    else:
        cliente.nombre = datos_reserva["nombre"]
        cliente.apellido = datos_reserva["apellido"]
        cliente.telefono = datos_reserva["telefono"]
        cliente.correo = correo or cliente.correo
        cliente.save()

    return cliente


def iniciar_sesion(request):
    """Inicio de sesión único para clientes y administradores."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("panel_administracion")
        return redirect("panel_cliente")

    siguiente = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        formulario = AuthenticationForm(request, data=request.POST)
        if formulario.is_valid():
            usuario = formulario.get_user()
            iniciar_sesion_usuario(request, usuario)

            destino_seguro = url_segura(request, siguiente)
            if destino_seguro:
                return redirect(destino_seguro)

            if usuario.is_staff:
                return redirect("panel_administracion")
            return redirect("panel_cliente")
    else:
        formulario = AuthenticationForm(request)

    return render(
        request,
        "usuarios/iniciar_sesion.html",
        {
            "formulario": formulario,
            "siguiente": siguiente or "",
        },
    )


def registrar_cliente(request):
    """Permite que un visitante cree una cuenta de cliente."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("panel_administracion")
        return redirect("panel_cliente")

    siguiente = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        formulario = FormularioRegistroCliente(request.POST)
        if formulario.is_valid():
            usuario = formulario.save()
            iniciar_sesion_usuario(request, usuario)
            messages.success(request, "Cuenta creada correctamente. Ya puedes reservar y consultar tu historial.")

            destino_seguro = url_segura(request, siguiente)
            if destino_seguro:
                return redirect(destino_seguro)
            return redirect("panel_cliente")
    else:
        formulario = FormularioRegistroCliente()

    return render(
        request,
        "usuarios/registro_cliente.html",
        {
            "formulario": formulario,
            "siguiente": siguiente or "",
        },
    )


def inicio(request):
    habitaciones_destacadas = (
        Habitacion.objects.select_related("tipo_habitacion")
        .prefetch_related("imagenes", "servicios")
        .filter(estado="disponible")[:3]
    )

    return render(
        request,
        "inicio.html",
        {
            "habitaciones_destacadas": habitaciones_destacadas,
        },
    )


def listar_habitaciones(request):
    formulario = FormularioBusquedaDisponibilidad(request.GET or None)
    habitaciones = obtener_habitaciones_disponibles()
    fechas_filtradas = False
    fecha_entrada = None
    fecha_salida = None
    personas = None

    if formulario.is_valid():
        fecha_entrada = formulario.cleaned_data.get("fecha_entrada")
        fecha_salida = formulario.cleaned_data.get("fecha_salida")
        personas = formulario.cleaned_data.get("personas")
        fechas_filtradas = bool(fecha_entrada and fecha_salida)

        habitaciones = obtener_habitaciones_disponibles(
            fecha_entrada=fecha_entrada,
            fecha_salida=fecha_salida,
            personas=personas,
        )

    return render(
        request,
        "habitaciones/listar_habitaciones.html",
        {
            "formulario": formulario,
            "habitaciones": habitaciones,
            "fechas_filtradas": fechas_filtradas,
            "fecha_entrada": fecha_entrada,
            "fecha_salida": fecha_salida,
            "personas": personas,
        },
    )


def detalle_habitacion(request, habitacion_id):
    habitacion = get_object_or_404(
        Habitacion.objects.select_related("tipo_habitacion").prefetch_related("imagenes", "servicios"),
        pk=habitacion_id,
        estado="disponible",
    )

    comentarios = (
        ComentarioHabitacion.objects.select_related("reserva__cliente")
        .filter(reserva__habitacion=habitacion, aprobado=True)
        .order_by("-fecha_comentario")
    )

    promedio_puntuacion = comentarios.aggregate(promedio=Avg("puntuacion"))["promedio"]
    ruta_reserva = reverse("crear_reserva", args=[habitacion.id])
    if request.GET.urlencode():
        ruta_reserva = f"{ruta_reserva}?{request.GET.urlencode()}"

    return render(
        request,
        "habitaciones/detalle_habitacion.html",
        {
            "habitacion": habitacion,
            "comentarios": comentarios,
            "promedio_puntuacion": promedio_puntuacion,
            "ruta_reserva": ruta_reserva,
        },
    )


@login_required(login_url="login")
def crear_reserva(request, habitacion_id):
    """Primer paso del flujo público: datos de la estadía antes del pago."""
    if request.user.is_staff:
        messages.info(request, "El panel administrativo gestiona reservas internas. Para probar como cliente, cierra sesión y crea una cuenta de cliente.")
        return redirect("panel_administracion")

    habitacion = get_object_or_404(Habitacion, pk=habitacion_id, estado="disponible")
    cliente = obtener_perfil_cliente(request.user)

    datos_iniciales = {
        "fecha_entrada": request.GET.get("fecha_entrada", ""),
        "fecha_salida": request.GET.get("fecha_salida", ""),
        "cantidad_personas": request.GET.get("personas", ""),
    }

    if cliente:
        datos_iniciales.update(
            {
                "nombre": cliente.nombre,
                "apellido": cliente.apellido,
                "dpi": cliente.dpi or "",
                "telefono": cliente.telefono,
                "correo": cliente.correo or request.user.email,
            }
        )

    if request.method == "POST":
        formulario = FormularioReservaCliente(request.POST, habitacion=habitacion, cliente=cliente)
        if formulario.is_valid():
            request.session[CLAVE_RESERVA_EN_SESION] = formulario.obtener_datos_para_pago()
            request.session.modified = True
            return redirect("pagar_reserva_cliente")
    else:
        formulario = FormularioReservaCliente(initial=datos_iniciales, habitacion=habitacion, cliente=cliente)

    return render(
        request,
        "reservas/crear_reserva.html",
        {
            "formulario": formulario,
            "habitacion": habitacion,
            "cliente": cliente,
        },
    )


@login_required(login_url="login")
def pagar_reserva_cliente(request):
    """Segundo paso del flujo público: pago y confirmación de reserva."""
    if request.user.is_staff:
        return redirect("panel_administracion")

    datos_reserva = request.session.get(CLAVE_RESERVA_EN_SESION)
    if not datos_reserva:
        messages.warning(request, "Primero debes seleccionar una habitación y completar tus datos.")
        return redirect("listar_habitaciones")

    habitacion = get_object_or_404(Habitacion, pk=datos_reserva["habitacion_id"], estado="disponible")
    fecha_entrada = convertir_fecha(datos_reserva["fecha_entrada"])
    fecha_salida = convertir_fecha(datos_reserva["fecha_salida"])
    noches, total_reserva = calcular_total_reserva(habitacion, fecha_entrada, fecha_salida)

    if obtener_reservas_cruzadas(habitacion, fecha_entrada, fecha_salida).exists():
        del request.session[CLAVE_RESERVA_EN_SESION]
        messages.error(
            request,
            "La habitación fue reservada por otra persona en esas fechas. Por favor elige otro rango o habitación.",
        )
        return redirect("listar_habitaciones")

    if request.method == "POST":
        formulario = FormularioPagoCliente(request.POST, total_reserva=total_reserva)
        if formulario.is_valid():
            try:
                with transaction.atomic():
                    cliente = crear_o_actualizar_cliente(datos_reserva, usuario=request.user)
                    estado_confirmada, _ = EstadoReserva.objects.get_or_create(
                        nombre="Confirmada",
                        defaults={"descripcion": "Reserva confirmada mediante pago del cliente."},
                    )

                    reserva = Reserva.objects.create(
                        cliente=cliente,
                        habitacion=habitacion,
                        estado_reserva=estado_confirmada,
                        fecha_entrada=fecha_entrada,
                        fecha_salida=fecha_salida,
                        cantidad_personas=datos_reserva["cantidad_personas"],
                        observaciones=datos_reserva.get("observaciones", ""),
                    )

                    Pago.objects.create(
                        reserva=reserva,
                        metodo_pago=formulario.cleaned_data["metodo_pago"],
                        monto=total_reserva,
                        monto_recibido=formulario.cleaned_data["monto_recibido"],
                        cambio=formulario.cambio,
                        referencia=formulario.cleaned_data.get("referencia", ""),
                        observaciones="Pago registrado por el cliente al confirmar la reserva.",
                    )

                del request.session[CLAVE_RESERVA_EN_SESION]
                messages.success(request, "Reserva confirmada correctamente. El pago fue registrado.")
                return redirect("reserva_exitosa", codigo_reserva=reserva.codigo_reserva)
            except ValidationError as error:
                messages.error(
                    request,
                    f"No fue posible confirmar la reserva: {error}",
                )
    else:
        formulario = FormularioPagoCliente(total_reserva=total_reserva)

    return render(
        request,
        "reservas/pagar_reserva.html",
        {
            "formulario": formulario,
            "datos_reserva": datos_reserva,
            "habitacion": habitacion,
            "fecha_entrada": fecha_entrada,
            "fecha_salida": fecha_salida,
            "noches": noches,
            "total_reserva": total_reserva,
        },
    )


def reserva_exitosa(request, codigo_reserva):
    reserva = get_object_or_404(
        Reserva.objects.select_related("cliente", "habitacion", "estado_reserva").prefetch_related("pagos__metodo_pago"),
        codigo_reserva=codigo_reserva,
    )

    if request.user.is_authenticated and not request.user.is_staff:
        cliente = obtener_perfil_cliente(request.user)
        if cliente is None or reserva.cliente_id != cliente.id:
            raise Http404("Reserva no encontrada.")

    pago = reserva.pagos.order_by("-fecha_pago").first()

    return render(
        request,
        "reservas/reserva_exitosa.html",
        {
            "reserva": reserva,
            "pago": pago,
        },
    )


@login_required(login_url="login")
def panel_cliente(request):
    """Panel privado donde el cliente consulta sus propias reservas."""
    if request.user.is_staff:
        return redirect("panel_administracion")

    cliente = obtener_perfil_cliente(request.user)
    if cliente is None:
        messages.warning(request, "Tu usuario no tiene un perfil de cliente asociado. Crea una cuenta de cliente nuevamente o consulta con administración.")
        return redirect("inicio")

    reservas = (
        Reserva.objects.select_related("habitacion", "estado_reserva")
        .prefetch_related("pagos__metodo_pago")
        .filter(cliente=cliente)
        .order_by("-fecha_creacion")
    )

    hoy = timezone.localdate()
    reservas_activas = reservas.filter(
        estado_reserva__nombre="Confirmada",
        fecha_salida__gte=hoy,
    )

    contexto = {
        "cliente": cliente,
        "reservas": reservas,
        "reservas_activas": reservas_activas,
        "total_reservas": reservas.count(),
        "reservas_confirmadas": reservas.filter(estado_reserva__nombre="Confirmada").count(),
        "reservas_pendientes": reservas.filter(estado_reserva__nombre="Pendiente").count(),
        "reservas_canceladas": reservas.filter(estado_reserva__nombre="Cancelada").count(),
    }
    return render(request, "clientes/panel_cliente.html", contexto)


@login_required(login_url="login")
def detalle_reserva_cliente(request, codigo_reserva):
    """Detalle privado de una reserva perteneciente al cliente autenticado."""
    if request.user.is_staff:
        return redirect("panel_administracion")

    cliente = obtener_perfil_cliente(request.user)
    if cliente is None:
        raise Http404("Cliente no encontrado.")

    reserva = get_object_or_404(
        Reserva.objects.select_related("cliente", "habitacion", "estado_reserva").prefetch_related("pagos__metodo_pago"),
        codigo_reserva=codigo_reserva,
        cliente=cliente,
    )

    pago = reserva.pagos.order_by("-fecha_pago").first()
    return render(request, "clientes/detalle_reserva_cliente.html", {"reserva": reserva, "pago": pago})


@user_passes_test(usuario_es_administrador, login_url="login")
def panel_administracion(request):
    hoy = timezone.localdate()

    total_habitaciones = Habitacion.objects.count()
    habitaciones_disponibles = Habitacion.objects.filter(estado="disponible").count()
    reservas_pendientes = Reserva.objects.filter(estado_reserva__nombre="Pendiente").count()
    reservas_confirmadas = Reserva.objects.filter(estado_reserva__nombre="Confirmada").count()
    ingresos_registrados = Pago.objects.aggregate(total=Sum("monto"))["total"] or 0

    proximas_reservas = (
        Reserva.objects.select_related("cliente", "habitacion", "estado_reserva")
        .filter(fecha_entrada__gte=hoy)
        .order_by("fecha_entrada")[:8]
    )

    return render(
        request,
        "administracion/dashboard.html",
        {
            "total_habitaciones": total_habitaciones,
            "habitaciones_disponibles": habitaciones_disponibles,
            "reservas_pendientes": reservas_pendientes,
            "reservas_confirmadas": reservas_confirmadas,
            "ingresos_registrados": ingresos_registrados,
            "proximas_reservas": proximas_reservas,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def panel_habitaciones(request):
    estado = request.GET.get("estado", "")
    busqueda = request.GET.get("q", "")

    habitaciones = (
        Habitacion.objects.select_related("tipo_habitacion")
        .prefetch_related("imagenes", "servicios")
        .all()
    )

    if estado:
        habitaciones = habitaciones.filter(estado=estado)

    if busqueda:
        habitaciones = habitaciones.filter(
            Q(numero__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(tipo_habitacion__nombre__icontains=busqueda)
        )

    return render(
        request,
        "administracion/habitaciones_lista.html",
        {
            "habitaciones": habitaciones,
            "estado_actual": estado,
            "busqueda": busqueda,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def crear_habitacion(request):
    if request.method == "POST":
        formulario = FormularioHabitacion(request.POST)
        if formulario.is_valid():
            habitacion = formulario.save()
            messages.success(request, "Habitación creada correctamente.")
            return redirect("editar_habitacion", habitacion_id=habitacion.id)
    else:
        formulario = FormularioHabitacion()

    return render(
        request,
        "administracion/habitacion_formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nueva habitación",
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def editar_habitacion(request, habitacion_id):
    habitacion = get_object_or_404(
        Habitacion.objects.prefetch_related("imagenes", "servicios"),
        pk=habitacion_id,
    )

    if request.method == "POST":
        formulario = FormularioHabitacion(request.POST, instance=habitacion)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Habitación actualizada correctamente.")
            return redirect("panel_habitaciones")
    else:
        formulario = FormularioHabitacion(instance=habitacion)

    formulario_imagen = FormularioImagenHabitacion()

    return render(
        request,
        "administracion/habitacion_formulario.html",
        {
            "formulario": formulario,
            "formulario_imagen": formulario_imagen,
            "habitacion": habitacion,
            "titulo": "Editar habitación",
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def desactivar_habitacion(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, pk=habitacion_id)

    if request.method == "POST":
        habitacion.estado = "inactiva"
        habitacion.save(update_fields=["estado", "fecha_actualizacion"])
        messages.warning(request, "La habitación fue desactivada. No se eliminó el historial.")
        return redirect("panel_habitaciones")

    return render(
        request,
        "administracion/confirmar_desactivar_habitacion.html",
        {
            "habitacion": habitacion,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def agregar_imagen_habitacion(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, pk=habitacion_id)

    if request.method == "POST":
        formulario = FormularioImagenHabitacion(request.POST, request.FILES)
        if formulario.is_valid():
            imagen = formulario.save(commit=False)
            imagen.habitacion = habitacion

            if imagen.es_principal:
                ImagenHabitacion.objects.filter(habitacion=habitacion).update(es_principal=False)

            imagen.save()
            messages.success(request, "Imagen agregada correctamente.")

    return redirect("editar_habitacion", habitacion_id=habitacion.id)


@user_passes_test(usuario_es_administrador, login_url="login")
def eliminar_imagen_habitacion(request, imagen_id):
    imagen = get_object_or_404(ImagenHabitacion, pk=imagen_id)
    habitacion_id = imagen.habitacion_id

    if request.method == "POST":
        imagen.delete()
        messages.warning(request, "Imagen eliminada correctamente.")

    return redirect("editar_habitacion", habitacion_id=habitacion_id)


@user_passes_test(usuario_es_administrador, login_url="login")
def panel_reservas(request):
    estado_id = request.GET.get("estado", "")
    busqueda = request.GET.get("q", "")

    reservas = Reserva.objects.select_related(
        "cliente",
        "habitacion",
        "estado_reserva",
    ).all()

    if estado_id:
        reservas = reservas.filter(estado_reserva_id=estado_id)

    if busqueda:
        reservas = reservas.filter(
            Q(codigo_reserva__icontains=busqueda)
            | Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__apellido__icontains=busqueda)
            | Q(habitacion__numero__icontains=busqueda)
        )

    estados = EstadoReserva.objects.all()

    return render(
        request,
        "administracion/reservas_lista.html",
        {
            "reservas": reservas,
            "estados": estados,
            "estado_actual": estado_id,
            "busqueda": busqueda,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def detalle_reserva_admin(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "cliente",
            "habitacion",
            "estado_reserva",
        ).prefetch_related("pagos__metodo_pago"),
        pk=reserva_id,
    )

    return render(
        request,
        "administracion/reserva_detalle.html",
        {
            "reserva": reserva,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)

    if request.method == "POST":
        formulario = FormularioReservaAdmin(request.POST, instance=reserva)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Reserva actualizada correctamente.")
            return redirect("detalle_reserva_admin", reserva_id=reserva.id)
    else:
        formulario = FormularioReservaAdmin(instance=reserva)

    return render(
        request,
        "administracion/reserva_formulario.html",
        {
            "formulario": formulario,
            "reserva": reserva,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def registrar_pago(request, reserva_id):
    """Registro manual de pagos desde administración, útil para pagos presenciales o ajustes."""
    reserva = get_object_or_404(Reserva, pk=reserva_id)

    if request.method == "POST":
        formulario = FormularioPago(request.POST)
        if formulario.is_valid():
            pago = formulario.save(commit=False)
            pago.reserva = reserva
            pago.save()
            messages.success(request, "Pago manual registrado correctamente.")
            return redirect("detalle_reserva_admin", reserva_id=reserva.id)
    else:
        formulario = FormularioPago(initial={"monto": reserva.saldo_pendiente})

    return render(
        request,
        "administracion/pago_formulario.html",
        {
            "formulario": formulario,
            "reserva": reserva,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def panel_tipos_habitacion(request):
    tipos = TipoHabitacion.objects.annotate(total_habitaciones=Count("habitaciones"))

    return render(
        request,
        "administracion/tipos_lista.html",
        {
            "tipos": tipos,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def crear_tipo_habitacion(request):
    if request.method == "POST":
        formulario = FormularioTipoHabitacion(request.POST)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Tipo de habitación creado correctamente.")
            return redirect("panel_tipos_habitacion")
    else:
        formulario = FormularioTipoHabitacion()

    return render(
        request,
        "administracion/tipo_formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nuevo tipo de habitación",
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def editar_tipo_habitacion(request, tipo_id):
    tipo = get_object_or_404(TipoHabitacion, pk=tipo_id)

    if request.method == "POST":
        formulario = FormularioTipoHabitacion(request.POST, instance=tipo)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Tipo de habitación actualizado correctamente.")
            return redirect("panel_tipos_habitacion")
    else:
        formulario = FormularioTipoHabitacion(instance=tipo)

    return render(
        request,
        "administracion/tipo_formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar tipo de habitación",
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def panel_servicios(request):
    servicios = Servicio.objects.annotate(total_habitaciones=Count("habitaciones"))

    return render(
        request,
        "administracion/servicios_lista.html",
        {
            "servicios": servicios,
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def crear_servicio(request):
    if request.method == "POST":
        formulario = FormularioServicio(request.POST)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Servicio creado correctamente.")
            return redirect("panel_servicios")
    else:
        formulario = FormularioServicio()

    return render(
        request,
        "administracion/servicio_formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nuevo servicio",
        },
    )


@user_passes_test(usuario_es_administrador, login_url="login")
def editar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)

    if request.method == "POST":
        formulario = FormularioServicio(request.POST, instance=servicio)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Servicio actualizado correctamente.")
            return redirect("panel_servicios")
    else:
        formulario = FormularioServicio(instance=servicio)

    return render(
        request,
        "administracion/servicio_formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar servicio",
        },
    )
