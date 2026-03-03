from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0007_producto_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='metodo_pago',
            field=models.CharField(choices=[('EFECTIVO', 'Efectivo'), ('TARJETA', 'Tarjeta'), ('TRANSFERENCIA', 'Transferencia')], default='EFECTIVO', max_length=20),
        ),
        migrations.AddField(
            model_name='venta',
            name='estado',
            field=models.CharField(choices=[('BORRADOR', 'Borrador'), ('PAGADA', 'Pagada'), ('ANULADA', 'Anulada')], default='PAGADA', max_length=20),
        ),
        migrations.AddField(
            model_name='saleitem',
            name='descuento',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='saleitem',
            name='lote',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
