from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventario', '0010_solicitud_anulacion_venta'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='costo_compra',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
