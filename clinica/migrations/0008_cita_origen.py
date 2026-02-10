from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('clinica', '0007_cita_reminder'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='origen',
            field=models.CharField(choices=[('DIRECTA', 'Directa'), ('SOLICITUD', 'Solicitud')], default='DIRECTA', max_length=20),
        ),
    ]
