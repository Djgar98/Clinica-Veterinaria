from django.contrib.auth.models import Group

from .models import Staff

ROLE_DUENO = 'DUENO'
ROLE_VETERINARIO = 'VETERINARIO'
ROLE_ASISTENTE = 'ASISTENTE'
ROLE_INVENTARIO = 'INVENTARIO'
ROLE_ADMIN = 'ADMIN'

ROLE_CHOICES = [
    (ROLE_DUENO, 'Dueño de mascota'),
    (ROLE_VETERINARIO, 'Veterinario'),
    (ROLE_ASISTENTE, 'Asistente'),
    (ROLE_INVENTARIO, 'Inventario'),
    (ROLE_ADMIN, 'Administrador'),
]

ROLE_GROUPS = {ROLE_DUENO, ROLE_VETERINARIO, ROLE_ASISTENTE, ROLE_INVENTARIO, ROLE_ADMIN}
STAFF_ROLES = {ROLE_VETERINARIO, ROLE_ASISTENTE, ROLE_ADMIN, ROLE_INVENTARIO}


def ensure_role_groups():
    for role_name in ROLE_GROUPS:
        Group.objects.get_or_create(name=role_name)


def get_user_roles(user):
    return set(user.groups.filter(name__in=ROLE_GROUPS).values_list('name', flat=True))


def has_role(user, role):
    return user.groups.filter(name=role).exists()


def is_owner_only(user):
    if not user or not user.is_authenticated:
        return False
    if not has_role(user, ROLE_DUENO):
        return False
    return not user.groups.filter(name__in=STAFF_ROLES).exists()


def get_user_role(user):
    """Return a primary role (for display) based on priority."""
    for role in [ROLE_ADMIN, ROLE_VETERINARIO, ROLE_ASISTENTE, ROLE_INVENTARIO, ROLE_DUENO]:
        if user.groups.filter(name=role).exists():
            return role
    if user.is_staff:
        return ROLE_ADMIN
    return ROLE_DUENO


def set_user_roles(user, roles, cargo=None, staff_active=True):
    ensure_role_groups()
    roles = set(roles or [])
    is_staff_role = bool(roles & STAFF_ROLES)
    user.is_staff = is_staff_role
    user.save()

    # Replace groups with selected roles only
    for role_name in ROLE_GROUPS:
        group = Group.objects.get(name=role_name)
        user.groups.remove(group)
    for role in roles:
        user.groups.add(Group.objects.get(name=role))

    if is_staff_role:
        if not cargo:
            if ROLE_ADMIN in roles:
                cargo = 'ADMIN'
            elif ROLE_VETERINARIO in roles:
                cargo = 'VETERINARIO'
            elif ROLE_ASISTENTE in roles:
                cargo = 'ASISTENTE'
            elif ROLE_INVENTARIO in roles:
                cargo = 'INVENTARIO'
            else:
                cargo = 'ADMIN'
        nombre = f"{user.first_name} {user.last_name}".strip() or user.username
        Staff.objects.update_or_create(
            user=user,
            defaults={
                'nombre_completo': nombre,
                'cargo': cargo or 'ADMIN',
                'is_active': staff_active,
            }
        )
    else:
        Staff.objects.filter(user=user).delete()


def set_user_role(user, role, cargo=None, staff_active=True):
    """Backwards-compatible single role setter."""
    return set_user_roles(user, [role], cargo=cargo, staff_active=staff_active)
