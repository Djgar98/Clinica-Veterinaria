from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from inventario.models import Producto


class Command(BaseCommand):
    help = 'Envia alertas de stock bajo por email.'

    def handle(self, *args, **options):
        if not getattr(settings, 'INVENTARIO_STOCK_ALERT_ENABLED', True):
            self.stdout.write('Alertas de stock deshabilitadas.')
            return
        recipients = getattr(settings, 'INVENTARIO_ALERT_RECIPIENTS', [])
        if not recipients:
            self.stdout.write('No hay destinatarios configurados (INVENTARIO_ALERT_RECIPIENTS).')
            return
        qs = Producto.objects.filter(is_active=True).exclude(tipo=Producto.TIPO_SERVICIO)
        qs = qs.filter(stock_inicial__lte=models.F('stock_minimo'))
        if not qs.exists():
            self.stdout.write('No hay productos con stock bajo.')
            return
        lines = [f"{p.nombre} (stock: {p.stock_inicial}, minimo: {p.stock_minimo})" for p in qs]
        body = "Productos con stock bajo:
" + "
".join(lines)
        send_mail(
            subject='Alerta de stock bajo',
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=recipients,
            fail_silently=True,
        )
        self.stdout.write(self.style.SUCCESS('Alertas enviadas.'))
