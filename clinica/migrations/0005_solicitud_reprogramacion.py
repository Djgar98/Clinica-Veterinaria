from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0004_solicitud_cita'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudReprogramacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nueva_fecha', models.DateTimeField()),
                ('descripcion', models.TextField()),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('APROBADA', 'Aprobada'), ('RECHAZADA', 'Rechazada')], default='PENDIENTE', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reprogramaciones', to='clinica.cita')),
                ('solicitado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
            ],
            options={
                'verbose_name': 'Solicitud de reprogramación',
                'verbose_name_plural': 'Solicitudes de reprogramación',
                'ordering': ['-created_at'],
            },
        ),
    ]
