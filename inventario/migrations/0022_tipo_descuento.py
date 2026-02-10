from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0021_venta_iva_rate_aplicado'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoDescuento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('MEDICAMENTO', 'Medicamento'), ('ACCESORIO', 'Accesorio'), ('SERVICIO', 'Servicio')], max_length=20, unique=True)),
                ('descuento_pct', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('descuento_desde', models.DateField(blank=True, null=True)),
                ('descuento_hasta', models.DateField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Descuento por tipo',
                'verbose_name_plural': 'Descuentos por tipo',
            },
        ),
    ]
