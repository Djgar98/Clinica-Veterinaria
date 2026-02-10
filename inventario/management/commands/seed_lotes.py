from django.core.management.base import BaseCommand
from inventario.models import Producto, ProductoLote


class Command(BaseCommand):
    help = 'Crea lotes iniciales para medicamentos existentes con stock.'

    def handle(self, *args, **options):
        created = 0
        for prod in Producto.objects.filter(tipo=Producto.TIPO_MEDICAMENTO):
            if prod.stock_inicial <= 0:
                continue
            if prod.lotes.exists():
                continue
            ProductoLote.objects.create(
                producto=prod,
                lote=prod.lote or 'SIN-LOTE',
                fecha_vencimiento=prod.fecha_vencimiento,
                cantidad=prod.stock_inicial,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Lotes creados: {created}'))
