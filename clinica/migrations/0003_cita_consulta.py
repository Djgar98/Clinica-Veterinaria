from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0002_mascota_detalle'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(default=django.utils.timezone.now)),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('ATENDIDA', 'Atendida'), ('CANCELADA', 'Cancelada')], default='PENDIENTE', max_length=20)),
                ('notas', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
                ('mascota', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='citas', to='clinica.mascota')),
                ('veterinario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='citas', to='usuarios.staff')),
            ],
            options={
                'verbose_name': 'Cita',
                'verbose_name_plural': 'Citas',
                'ordering': ['fecha'],
            },
        ),
        migrations.AddField(
            model_name='consulta',
            name='cita',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consultas', to='clinica.cita'),
        ),
        migrations.AddField(
            model_name='consulta',
            name='estado',
            field=models.CharField(choices=[('ABIERTA', 'Abierta'), ('CERRADA', 'Cerrada')], default='ABIERTA', max_length=20),
        ),
        migrations.AddField(
            model_name='consulta',
            name='cerrada_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
