from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='telefono',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.CreateModel(
            name='OwnerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telefono', models.CharField(blank=True, max_length=30)),
                ('direccion', models.CharField(blank=True, max_length=200)),
                ('documento', models.CharField(blank=True, max_length=50)),
                ('contacto_emergencia', models.CharField(blank=True, max_length=200)),
                ('notas', models.TextField(blank=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='owner_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Propietario',
                'verbose_name_plural': 'Propietarios',
            },
        ),
    ]
