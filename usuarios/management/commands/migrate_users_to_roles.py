from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from clinica.models import Mascota
from usuarios.models import Staff
from usuarios.roles import (
    ROLE_DUENO,
    ROLE_VETERINARIO,
    ROLE_ASISTENTE,
    ROLE_INVENTARIO,
    ROLE_ADMIN,
    ROLE_GROUPS,
    set_user_role,
    get_user_role,
)


class Command(BaseCommand):
    help = 'Migra usuarios actuales a los nuevos roles detallados.'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()

        for user in users:
            # Skip if user already has a detailed role group
            if user.groups.filter(name__in=list(ROLE_GROUPS)).exists():
                continue

            if user.is_superuser:
                set_user_role(user, ROLE_ADMIN, cargo='ADMIN', staff_active=True)
                continue

            staff = Staff.objects.filter(user=user).first()
            if staff:
                if staff.cargo == 'VETERINARIO':
                    role = ROLE_VETERINARIO
                elif staff.cargo == 'ASISTENTE':
                    role = ROLE_ASISTENTE
                elif staff.cargo == 'ADMIN':
                    role = ROLE_ADMIN
                else:
                    role = ROLE_ASISTENTE
                set_user_role(user, role, cargo=staff.cargo, staff_active=staff.is_active)
                continue

            # Old STAFF group => ASISTENTE by default
            if user.groups.filter(name='STAFF').exists() or user.is_staff:
                set_user_role(user, ROLE_ASISTENTE, cargo='ASISTENTE', staff_active=True)
                continue

            # Owners (has mascotas) => DUENO
            if Mascota.objects.filter(owner=user).exists():
                set_user_role(user, ROLE_DUENO)
                continue

            # Default to DUENO
            set_user_role(user, ROLE_DUENO)

        self.stdout.write(self.style.SUCCESS('Migración de roles completada.'))
