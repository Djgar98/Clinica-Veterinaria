from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('clinica', '0006_solicitud_reprogramacion_rechazo'),
    ]

    operations = [
        migrations.CreateModel(
            name='CitaReminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canal', models.CharField(choices=[('EMAIL', 'Email'), ('WHATSAPP', 'WhatsApp')], max_length=20)),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('ENVIADO', 'Enviado'), ('FALLIDO', 'Fallido'), ('OMITIDO', 'Omitido')], default='PENDIENTE', max_length=20)),
                ('programado_para', models.DateTimeField()),
                ('enviado_en', models.DateTimeField(blank=True, null=True)),
                ('destinatario', models.CharField(blank=True, max_length=200)),
                ('error', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recordatorios', to='clinica.cita')),
            ],
            options={
                'verbose_name': 'Recordatorio de cita',
                'verbose_name_plural': 'Recordatorios de citas',
                'ordering': ['-programado_para'],
            },
        ),
    ]
