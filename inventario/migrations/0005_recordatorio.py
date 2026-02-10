from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0004_venta_stock_committed'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Recordatorio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('tipo', models.CharField(choices=[('ENTRADA', 'Entrada de producto'), ('PROVEEDOR', 'Visita de proveedor')], max_length=20)),
                ('fecha', models.DateTimeField()),
                ('proveedor', models.CharField(blank=True, max_length=200)),
                ('cantidad', models.PositiveIntegerField(blank=True, null=True)),
                ('notas', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('COMPLETADO', 'Completado')], default='PENDIENTE', max_length=20)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('producto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recordatorios', to='inventario.producto')),
            ],
            options={
                'verbose_name': 'Recordatorio',
                'verbose_name_plural': 'Recordatorios',
                'ordering': ['fecha'],
            },
        ),
    ]
