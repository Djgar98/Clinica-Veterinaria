from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Assign existing users to default groups using simple heuristics.'

    def handle(self, *args, **options):
        User = get_user_model()
        groups = {}
        for name in ['Administradores', 'Vendedores', 'Veterinarios', 'Recepcion']:
            try:
                groups[name] = Group.objects.get(name=name)
            except Group.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Group not found: {name}'))

        users = User.objects.all()
        for u in users:
            added = []
            if u.is_superuser:
                g = groups.get('Administradores')
                if g:
                    g.user_set.add(u); added.append('Administradores')
            elif u.is_staff:
                g = groups.get('Vendedores') or groups.get('Administradores')
                if g:
                    g.user_set.add(u); added.append(g.name)
            # heuristic: username/email contains vet
            uname = (u.username or '').lower()
            email = (u.email or '').lower()
            if 'vet' in uname or 'vet' in email or 'veter' in uname or 'veter' in email:
                g = groups.get('Veterinarios')
                if g:
                    g.user_set.add(u); added.append('Veterinarios')
            if 'recep' in uname or 'recep' in email or 'recepcion' in uname or 'recepcion' in email:
                g = groups.get('Recepcion')
                if g:
                    g.user_set.add(u); added.append('Recepcion')

            if added:
                self.stdout.write(self.style.SUCCESS(f'Assigned {u.username} to: {", ".join(added)}'))
            else:
                self.stdout.write(f'No assignment rules matched for {u.username}')

        self.stdout.write(self.style.SUCCESS('User assignment complete.'))
