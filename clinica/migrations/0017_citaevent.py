from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0016_solicitudcita_cita_asignada'),
    ]

    operations = [
        migrations.CreateModel(
            name='CitaEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('CREADA', 'Creada'), ('CONFIRMADA', 'Confirmada'), ('CANCELADA', 'Cancelada'), ('REPROG_SOLICITADA', 'Reprogramación solicitada'), ('REPROG_APROBADA', 'Reprogramación aprobada'), ('REPROG_RECHAZADA', 'Reprogramación rechazada'), ('ATENDIDA', 'Atendida'), ('ORIGEN_SOLICITUD', 'Origen: solicitud'), ('ORIGEN_DIRECTA', 'Origen: directa')], max_length=30)),
                ('detalle', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historial', to='clinica.cita')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Historial de cita',
                'verbose_name_plural': 'Historial de citas',
                'ordering': ['-created_at'],
            },
        ),
    ]
