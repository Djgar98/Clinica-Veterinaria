from django.db import migrations


def forwards(apps, schema_editor):
    CitaReminder = apps.get_model('clinica', 'CitaReminder')
    CitaReminder.objects.filter(canal='EMAIL').update(canal='WHATSAPP')


class Migration(migrations.Migration):
    dependencies = [
        ('clinica', '0012_merge_20260206_0208'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
