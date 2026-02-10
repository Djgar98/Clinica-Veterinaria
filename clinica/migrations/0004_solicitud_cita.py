from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0003_cita_consulta'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudCita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_preferida', models.DateTimeField(blank=True, null=True)),
                ('motivo', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('ATENDIDA', 'Atendida'), ('RECHAZADA', 'Rechazada')], default='PENDIENTE', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('mascota', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_cita', to='clinica.mascota')),
                ('solicitado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
            ],
            options={
                'verbose_name': 'Solicitud de cita',
                'verbose_name_plural': 'Solicitudes de cita',
                'ordering': ['-created_at'],
            },
        ),
    ]
