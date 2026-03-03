from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0005_solicitud_reprogramacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudreprogramacion',
            name='motivo_rechazo',
            field=models.TextField(blank=True),
        ),
    ]
