from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from clinica.models import Mascota, Consulta, Expediente, Cita, SolicitudCita, SolicitudReprogramacion
from inventario.models import Producto, Venta, VentaAudit, SolicitudAnulacionVenta, InventoryMovement, StockAdjustmentRequest, ProductoLote


class Command(BaseCommand):
    help = 'Crea y asigna permisos a los grupos de roles del sistema.'

    def handle(self, *args, **options):
        groups = {
            'DUENO': [
                ('clinica', 'view_mascota'),
                ('clinica', 'view_expediente'),
                ('clinica', 'view_cita'),
                ('clinica', 'add_solicitudcita'),
                ('clinica', 'view_solicitudcita'),
                ('clinica', 'add_solicitudreprogramacion'),
                ('clinica', 'view_solicitudreprogramacion'),
            ],
            'VETERINARIO': [
                ('clinica', 'view_mascota'),
                ('clinica', 'view_expediente'),
                ('clinica', 'view_cita'),
                ('clinica', 'add_solicitudreprogramacion'),
                ('clinica', 'change_solicitudreprogramacion'),
                ('clinica', 'view_solicitudreprogramacion'),
                ('clinica', 'view_consulta'),
                ('clinica', 'add_consulta'),
                ('clinica', 'change_consulta'),
            ],
            'ASISTENTE': [
                ('clinica', 'view_mascota'),
                ('clinica', 'add_mascota'),
                ('clinica', 'change_mascota'),
                ('clinica', 'view_cita'),
                ('clinica', 'add_cita'),
                ('clinica', 'change_cita'),
                ('clinica', 'view_citareminder'),
                ('clinica', 'change_citareminder'),
                ('clinica', 'view_solicitudcita'),
                ('clinica', 'change_solicitudcita'),
                ('clinica', 'view_solicitudreprogramacion'),
                ('clinica', 'change_solicitudreprogramacion'),
                ('clinica', 'view_consulta'),
                ('clinica', 'add_consulta'),
                ('inventario', 'view_producto'),
                ('inventario', 'view_recordatorio'),
                ('inventario', 'add_recordatorio'),
                ('inventario', 'change_recordatorio'),
                ('inventario', 'delete_recordatorio'),
                ('inventario', 'view_venta'),
                ('inventario', 'add_venta'),
                ('inventario', 'change_venta'),
                ('inventario', 'add_solicitudanulacionventa'),
                ('inventario', 'view_inventorymovement'),
                ('inventario', 'view_productolote'),
                ('inventario', 'view_stockadjustmentrequest'),
                ('inventario', 'add_stockadjustmentrequest'),
            ],
            'INVENTARIO': [
                ('inventario', 'view_producto'),
                ('inventario', 'add_producto'),
                ('inventario', 'change_producto'),
                ('inventario', 'change_producto_stock'),
                ('inventario', 'change_producto_lote'),
                ('inventario', 'view_venta'),
                ('inventario', 'add_venta'),
                ('inventario', 'change_venta'),
                ('inventario', 'view_ventaaudit'),
                ('inventario', 'add_solicitudanulacionventa'),
                ('inventario', 'view_inventorymovement'),
                ('inventario', 'view_productolote'),
                ('inventario', 'view_stockadjustmentrequest'),
                ('inventario', 'add_stockadjustmentrequest'),
            ],
            'ADMIN': [
                ('clinica', '*'),
                ('inventario', '*'),
                ('usuarios', '*'),
                ('auth', '*'),
            ],
        }

        # Ensure content types exist
        ContentType.objects.get_for_model(Mascota)
        ContentType.objects.get_for_model(Consulta)
        ContentType.objects.get_for_model(Expediente)
        ContentType.objects.get_for_model(Cita)
        ContentType.objects.get_for_model(SolicitudCita)
        ContentType.objects.get_for_model(SolicitudReprogramacion)
        ContentType.objects.get_for_model(Producto)
        ContentType.objects.get_for_model(ProductoLote)
        ContentType.objects.get_for_model(Venta)
        ContentType.objects.get_for_model(VentaAudit)
        ContentType.objects.get_for_model(SolicitudAnulacionVenta)
        ContentType.objects.get_for_model(InventoryMovement)
        ContentType.objects.get_for_model(StockAdjustmentRequest)

        for group_name, perms in groups.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            group.permissions.clear()

            for app_label, codename in perms:
                if codename == '*':
                    app_perms = Permission.objects.filter(content_type__app_label=app_label)
                    group.permissions.add(*app_perms)
                else:
                    perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
                    if perm:
                        group.permissions.add(perm)

            self.stdout.write(self.style.SUCCESS(f'Grupo actualizado: {group_name}'))
