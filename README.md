# Posada El Descanso

Sistema web de reservas de habitaciones desarrollado con Django, Python, HTML, CSS, Bootstrap y JavaScript.

## Funciones principales

- Página pública con banner cálido y diseño tipo hotel/posada.
- Catálogo público de habitaciones.
- Búsqueda de habitaciones disponibles por fecha y cantidad de personas.
- Registro e inicio de sesión para clientes.
- Panel del cliente para consultar reservas, estados y pagos.
- Flujo de reserva en dos pasos: datos de estadía y confirmación de pago.
- Confirmación automática de la reserva cuando el cliente registra el pago.
- Panel administrativo protegido por usuario y contraseña.
- CRUD de habitaciones, tipos de habitación y servicios.
- Gestión administrativa de reservas e imágenes.
- Modelos con relaciones, índices y validaciones para evitar reservas cruzadas.
- Configuración preparada para GitHub, hosting y futura conexión con base de datos en Azure.

## Instalación local

```bash
cd posada_el_descanso
python -m venv .venv
```

Activar entorno virtual en Windows PowerShell:

```bash
.venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Copiar archivo de variables de entorno:

```bash
copy .env.example .env
```

Crear tablas y datos iniciales:

```bash
python manage.py migrate
python manage.py cargar_datos_iniciales
```

Crear administrador:

```bash
python manage.py createsuperuser
```

Ejecutar servidor:

```bash
python manage.py runserver
```

Abrir en el navegador:

```text
http://127.0.0.1:8000/
```

## Rutas principales

```text
/                         Página de inicio
/habitaciones/            Catálogo y disponibilidad
/clientes/registro/       Registro de cliente
/clientes/panel/          Panel privado del cliente
/login/                   Inicio de sesión para clientes y administradores
/panel/                   Panel administrativo
```

## Flujo recomendado de prueba

1. Ejecutar migraciones y datos iniciales.
2. Crear superusuario para el panel administrativo.
3. Entrar al sitio público.
4. Crear una cuenta de cliente.
5. Consultar habitaciones por fecha.
6. Reservar una habitación.
7. Confirmar el pago.
8. Revisar la reserva en “Mi cuenta”.
9. Iniciar sesión como administrador y revisar la reserva en el panel.

## Nota técnica

El entorno virtual `.venv`, el archivo `.env`, la base de datos local `db.sqlite3` y las carpetas generadas no deben subirse a GitHub. Ya están contempladas en `.gitignore`.
