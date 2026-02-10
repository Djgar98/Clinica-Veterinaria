from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0015_solicitudcita_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudcita',
            name='cita_asignada',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='solicitudes_origen', to='clinica.cita'),
        ),
    ]
