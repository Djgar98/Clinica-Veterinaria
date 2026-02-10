from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mascota',
            name='color',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='mascota',
            name='tamanio',
            field=models.CharField(blank=True, choices=[('PEQ', 'Pequeño'), ('MED', 'Mediano'), ('GRA', 'Grande')], max_length=3),
        ),
        migrations.AddField(
            model_name='mascota',
            name='peso_kg',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='mascota',
            name='esterilizado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mascota',
            name='microchip',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='mascota',
            name='alergias',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='mascota',
            name='vacunas',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='mascota',
            name='senas_particulares',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='mascota',
            name='notas',
            field=models.TextField(blank=True),
        ),
    ]
