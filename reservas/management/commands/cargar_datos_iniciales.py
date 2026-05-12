from django.core.management.base import BaseCommand

from reservas.models import EstadoReserva, Habitacion, HabitacionServicio, MetodoPago, Servicio, TipoHabitacion


class Command(BaseCommand):
    help = "Carga catálogos y habitaciones de ejemplo para probar el sistema."

    def handle(self, *args, **options):
        estados = [
            ("Pendiente", "Reserva recibida, pendiente de confirmación."),
            ("Confirmada", "Reserva aprobada por administración."),
            ("Cancelada", "Reserva cancelada."),
            ("Finalizada", "Estadía finalizada."),
            ("No presentada", "El cliente no se presentó."),
        ]

        for nombre, descripcion in estados:
            EstadoReserva.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion})

        metodos = [
            ("Efectivo", "Pago recibido en efectivo."),
            ("Transferencia", "Pago por transferencia bancaria."),
            ("Tarjeta", "Pago con tarjeta."),
            ("Depósito", "Pago mediante depósito bancario."),
        ]

        for nombre, descripcion in metodos:
            MetodoPago.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion})

        servicios = [
            ("WiFi", "Internet inalámbrico."),
            ("Parqueo", "Espacio de parqueo."),
            ("Agua caliente", "Ducha con agua caliente."),
            ("TV", "Televisión en la habitación."),
            ("Baño privado", "Baño privado dentro de la habitación."),
            ("Vista al jardín", "Vista hacia áreas verdes."),
        ]

        servicios_creados = []
        for nombre, descripcion in servicios:
            servicio, _ = Servicio.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion},
            )
            servicios_creados.append(servicio)

        tipo_individual, _ = TipoHabitacion.objects.get_or_create(
            nombre="Individual",
            defaults={
                "descripcion": "Habitación cómoda para una persona.",
                "capacidad_base": 1,
            },
        )

        tipo_doble, _ = TipoHabitacion.objects.get_or_create(
            nombre="Doble",
            defaults={
                "descripcion": "Habitación para dos personas.",
                "capacidad_base": 2,
            },
        )

        tipo_familiar, _ = TipoHabitacion.objects.get_or_create(
            nombre="Familiar",
            defaults={
                "descripcion": "Habitación amplia para familias.",
                "capacidad_base": 4,
            },
        )

        habitaciones = [
            {
                "numero": "101",
                "nombre": "Habitación Individual Jardín",
                "tipo_habitacion": tipo_individual,
                "descripcion": "Habitación acogedora con ambiente tranquilo y vista parcial al jardín.",
                "capacidad_maxima": 1,
                "precio_por_noche": 225,
            },
            {
                "numero": "102",
                "nombre": "Habitación Doble Confort",
                "tipo_habitacion": tipo_doble,
                "descripcion": "Espacio cómodo para dos personas, ideal para descanso de fin de semana.",
                "capacidad_maxima": 2,
                "precio_por_noche": 350,
            },
            {
                "numero": "201",
                "nombre": "Habitación Familiar",
                "tipo_habitacion": tipo_familiar,
                "descripcion": "Habitación amplia para familias pequeñas, con buena iluminación natural.",
                "capacidad_maxima": 4,
                "precio_por_noche": 575,
            },
        ]

        for datos in habitaciones:
            habitacion, _ = Habitacion.objects.get_or_create(
                numero=datos["numero"],
                defaults=datos,
            )
            for servicio in servicios_creados[:5]:
                HabitacionServicio.objects.get_or_create(
                    habitacion=habitacion,
                    servicio=servicio,
                )

        self.stdout.write(self.style.SUCCESS("Datos iniciales cargados correctamente."))
