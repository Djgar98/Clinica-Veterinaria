from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from clinica.models import Cita, CitaReminder


class Command(BaseCommand):
    help = 'Crea recordatorios de cita de ejemplo (pendientes) para ver en el dashboard.'

    def handle(self, *args, **options):
        now = timezone.now()
        citas = Cita.objects.filter(fecha__gte=now).order_by('fecha')[:3]
        if not citas:
            self.stdout.write(self.style.ERROR('No hay citas futuras. Crea una cita primero.'))
            return

        created = 0
        for cita in citas:
            for canal in [CitaReminder.CANAL_WHATSAPP]:
                exists = CitaReminder.objects.filter(
                    cita=cita,
                    canal=canal,
                    estado=CitaReminder.ESTADO_PENDIENTE,
                ).exists()
                if exists:
                    continue
                CitaReminder.objects.create(
                    cita=cita,
                    canal=canal,
                    estado=CitaReminder.ESTADO_PENDIENTE,
                    programado_para=cita.fecha - timedelta(hours=24),
                    destinatario='demo@example.com',
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Recordatorios creados: {created}'))
