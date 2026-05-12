from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as vistas_autenticacion
from django.urls import include, path

from reservas import views as vistas_reservas


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("reservas.urls")),
    path("login/", vistas_reservas.iniciar_sesion, name="login"),
    path(
        "logout/",
        vistas_autenticacion.LogoutView.as_view(),
        name="logout",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
