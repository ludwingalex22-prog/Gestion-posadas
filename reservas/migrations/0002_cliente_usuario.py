# Migración agregada para permitir cuentas de cliente sin alterar la estructura administrativa.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("reservas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="usuario",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cliente",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["usuario"], name="idx_cliente_usuario"),
        ),
    ]
