from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0006_producto_detalle'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='tipo',
            field=models.CharField(choices=[('MEDICAMENTO', 'Medicamento'), ('ACCESORIO', 'Accesorio')], default='ACCESORIO', max_length=20),
        ),
    ]
