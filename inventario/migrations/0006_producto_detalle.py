from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0005_recordatorio'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='codigo',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='producto',
            name='presentacion',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='producto',
            name='contenido',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='unidad_contenido',
            field=models.CharField(blank=True, choices=[('ml', 'ml'), ('mg', 'mg'), ('g', 'g'), ('unidad', 'unidad'), ('tableta', 'tableta')], max_length=20),
        ),
        migrations.AddField(
            model_name='producto',
            name='lote',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='producto',
            name='fecha_vencimiento',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='proveedor',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
