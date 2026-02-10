from usuarios.roles import get_user_role, has_role, is_owner_only, ROLE_ADMIN, ROLE_ASISTENTE, ROLE_INVENTARIO
from usuarios.models import Notification


def main_nav(request):
    """Return a list of main navigation items (label, url_name, perm) to render in the navbar.

    perm can be None to always show. url_name is a dotted name suitable for {% url %}.
    """
    user = request.user
    items = [
        { 'label': 'Inicio', 'url': 'clinica:dashboard', 'perm': None },
        { 'label': 'Mascotas', 'url': 'clinica:lista_mascotas', 'perm': 'clinica.view_mascota' },
        { 'label': 'Citas', 'url': 'clinica:cita_list', 'perm': 'clinica.view_cita' },
        { 'label': 'Solicitudes', 'url': 'clinica:solicitud_cita_list', 'perm': 'clinica.view_solicitudcita' },
        { 'label': 'Reprogramaciones', 'url': 'clinica:solicitud_reprogramacion_list', 'perm': 'clinica.view_solicitudreprogramacion' },
        { 'label': 'Inventario', 'url': 'inventario:list', 'perm': 'inventario.view_producto' },
        { 'label': 'Ventas', 'url': 'inventario:venta_list', 'perm': 'inventario.view_venta' },
        { 'label': 'Config Ventas', 'url': 'inventario:venta_config', 'perm': 'inventario.change_ventaconfig' },
        { 'label': 'Kardex', 'url': 'inventario:kardex_list', 'perm': 'inventario.view_inventorymovement' },
        { 'label': 'Ajustes', 'url': 'inventario:ajuste_list', 'perm': 'inventario.view_stockadjustmentrequest' },
        { 'label': 'Anulaciones', 'url': 'inventario:anulacion_list', 'perm': 'inventario.view_solicitudanulacionventa' },
        { 'label': 'Recordatorios', 'url': 'inventario:recordatorio_list', 'perm': 'inventario.view_recordatorio' },
        { 'label': 'Descuentos', 'url': 'inventario:producto_descuentos', 'perm': 'inventario.change_producto' },
        { 'label': 'Reportes', 'url': 'inventario:reportes', 'perm': 'inventario.view_venta' },
        { 'label': 'Accesos', 'url': 'usuarios:access_logs', 'perm': 'usuarios.view_accesslog' },
        { 'label': 'Auditoría', 'url': 'usuarios:audit_logs', 'perm': 'usuarios.view_auditlog' },
        { 'label': 'Usuarios', 'url': 'usuarios:list', 'perm': 'auth.view_user' },
        { 'label': 'Admin', 'url': 'admin:index', 'perm': 'auth.view_user' },
    ]
    role = get_user_role(user)
    is_admin = user.is_superuser or user.groups.filter(name='ADMIN').exists()
    is_inventory_nav = any([
        is_admin,
        has_role(user, ROLE_ASISTENTE),
        has_role(user, ROLE_INVENTARIO),
    ])
    # Filter by permission where needed
    filtered = []
    for it in items:
        perm = it.get('perm')
        if it.get('label') == 'Reportes' and not is_admin:
            continue
        if it.get('label') in ['Accesos', 'Auditoría'] and not is_admin:
            continue
        if not perm:
            filtered.append(it)
        else:
            if user.has_perm(perm):
                filtered.append(it)
    notif_list = []
    notif_unread = 0
    if user.is_authenticated:
        notif_list = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        notif_unread = Notification.objects.filter(user=user, read_at__isnull=True).count()
    return {
        'main_nav_items': filtered,
        'is_admin': is_admin,
        'role': role,
        'is_inventory_nav': is_inventory_nav,
        'is_owner_only': is_owner_only(user),
        'notifications_recent': notif_list,
        'notifications_unread': notif_unread,
    }
