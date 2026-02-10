from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from usuarios.models import Staff
from usuarios.roles import ROLE_GROUPS, STAFF_ROLES


class Command(BaseCommand):
    help = 'Crea perfiles Staff faltantes para usuarios con roles STAFF (incluye INVENTARIO).'

    def handle(self, *args, **options):
        User = get_user_model()
        created = 0
        for role in ROLE_GROUPS:
            if role not in STAFF_ROLES:
                continue
            users = User.objects.filter(groups__name=role).distinct()
            for user in users:
                nombre = f"{user.first_name} {user.last_name}".strip() or user.username
                obj, was_created = Staff.objects.get_or_create(
                    user=user,
                    defaults={
                        'nombre_completo': nombre,
                        'cargo': role,
                        'is_active': True,
                    }
                )
                if was_created:
                    created += 1
                else:
                    if not obj.cargo:
                        obj.cargo = role
                        obj.save(update_fields=['cargo'])
        self.stdout.write(self.style.SUCCESS(f'Perfiles Staff creados: {created}'))
