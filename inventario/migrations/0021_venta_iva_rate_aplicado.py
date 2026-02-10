from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0020_alter_ventaconfig_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='iva_rate_aplicado',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
    ]

