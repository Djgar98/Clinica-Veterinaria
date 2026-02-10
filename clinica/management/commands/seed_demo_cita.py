from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from clinica.models import Cita, Mascota
from usuarios.models import Staff


class Command(BaseCommand):
    help = 'Crea una cita de prueba para mostrar en el calendario.'

    def handle(self, *args, **options):
        mascota = Mascota.objects.order_by('id').first()
        if not mascota:
            self.stdout.write(self.style.ERROR('No hay mascotas. Crea una mascota primero.'))
            return

        staff = Staff.objects.filter(is_active=True).order_by('id').first()
        fecha = timezone.now() + timedelta(days=1)

        cita = Cita.objects.create(
            mascota=mascota,
            veterinario=staff,
            fecha=fecha,
            estado=Cita.ESTADO_CONFIRMADA,
            origen=Cita.ORIGEN_DIRECTA,
            notas='Cita de prueba (seed)',
        )
        self.stdout.write(self.style.SUCCESS(f'Cita creada: #{cita.id} para {mascota.nombre}'))
