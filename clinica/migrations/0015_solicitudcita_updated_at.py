from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0014_alter_citareminder_canal'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudcita',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, blank=True),
        ),
    ]
