from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventario', '0017_alter_producto_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='VentaConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descuento_habilitado', models.BooleanField(default=False)),
                ('iva_rate', models.DecimalField(choices=[('0', '0%'), ('0.15', '15%')], decimal_places=2, default=0.15, max_digits=4)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'ConfiguraciÃ³n de ventas',
                'verbose_name_plural': 'ConfiguraciÃ³n de ventas',
            },
        ),
    ]
