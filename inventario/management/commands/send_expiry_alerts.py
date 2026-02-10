from datetime import timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from inventario.models import Producto, ProductoLote


class Command(BaseCommand):
    help = 'Envia alertas de vencimiento de productos.'

    def handle(self, *args, **options):
        if not getattr(settings, 'INVENTARIO_VENCIMIENTO_ALERT_ENABLED', True):
            self.stdout.write('Alertas de vencimiento deshabilitadas.')
            return
        recipients = getattr(settings, 'INVENTARIO_ALERT_RECIPIENTS', [])
        if not recipients:
            self.stdout.write('No hay destinatarios configurados (INVENTARIO_ALERT_RECIPIENTS).')
            return
        dias = int(getattr(settings, 'INVENTARIO_VENCIMIENTO_DIAS', 30))
        limite = timezone.now().date() + timedelta(days=dias)
        qs = ProductoLote.objects.select_related('producto').filter(
            producto__is_active=True,
            producto__tipo=Producto.TIPO_MEDICAMENTO,
            fecha_vencimiento__isnull=False,
            cantidad__gt=0,
            fecha_vencimiento__lte=limite,
        )
        if not qs.exists():
            self.stdout.write('No hay productos por vencer.')
            return
        lines = [f"{l.producto.nombre} (vence: {l.fecha_vencimiento}, lote: {l.lote}, stock: {l.cantidad})" for l in qs]
        body = f"Productos que vencen en {dias} dias o menos:
" + "
".join(lines)
        send_mail(
            subject='Alerta de vencimientos',
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=recipients,
            fail_silently=True,
        )
        self.stdout.write(self.style.SUCCESS('Alertas enviadas.'))
