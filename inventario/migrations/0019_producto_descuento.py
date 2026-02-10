from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventario', '0018_venta_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='descuento_pct',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
        ),
        migrations.AddField(
            model_name='producto',
            name='descuento_desde',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='descuento_hasta',
            field=models.DateField(blank=True, null=True),
        ),
    ]
