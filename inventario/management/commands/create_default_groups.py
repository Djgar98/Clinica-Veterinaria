from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from inventario.models import Producto, Venta
from clinica.models import Mascota, Consulta


class Command(BaseCommand):
    help = 'Create default user groups and assign sensible permissions for the clinic.'

    def handle(self, *args, **options):
        groups = {
            'Administradores': {
                'perms': 'all',
            },
            'Vendedores': {
                'perms': [
                    'inventario.add_venta', 'inventario.change_venta', 'inventario.view_venta',
                    'inventario.view_producto',
                ]
            },
            'Veterinarios': {
                'perms': [
                    'clinica.add_consulta', 'clinica.view_consulta', 'clinica.view_mascota',
                ]
            },
            'Recepcion': {
                'perms': [
                    'clinica.add_mascota', 'clinica.change_mascota', 'clinica.view_mascota',
                    'inventario.view_producto',
                ]
            }
        }

        for name, info in groups.items():
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {name}'))
            else:
                self.stdout.write(f'Group already exists: {name}')
            if info['perms'] == 'all':
                # assign all perms for involved models
                perms = Permission.objects.all()
            else:
                perms = []
                for codename in info['perms']:
                    app_label, perm = codename.split('.')
                    try:
                        p = Permission.objects.get(content_type__app_label=app_label, codename=perm)
                        perms.append(p)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Permission not found: {codename}'))
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f'Assigned {len(perms)} permissions to {name}'))

        self.stdout.write(self.style.SUCCESS('Default groups setup complete.'))