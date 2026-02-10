from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0022_tipo_descuento'),
        ('clinica', '0017_citaevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Receta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('ACEPTADA', 'Aceptada'), ('RECHAZADA', 'Rechazada')], default='PENDIENTE', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('consulta', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receta', to='clinica.consulta')),
                ('mascota', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recetas', to='clinica.mascota')),
                ('venta', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recetas', to='inventario.venta')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Receta',
                'verbose_name_plural': 'Recetas',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RecetaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('lote', models.CharField(blank=True, max_length=80)),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='receta_items', to='inventario.producto')),
                ('receta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='clinica.receta')),
            ],
            options={
                'verbose_name': 'Item de receta',
                'verbose_name_plural': 'Items de receta',
            },
        ),
    ]
