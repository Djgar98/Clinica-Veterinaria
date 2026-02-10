from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP


class Categoria(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.name


class Producto(models.Model):
    TIPO_MEDICAMENTO = 'MEDICAMENTO'
    TIPO_ACCESORIO = 'ACCESORIO'
    TIPO_SERVICIO = 'SERVICIO'
    TIPO_CHOICES = [
        (TIPO_MEDICAMENTO, 'Medicamento'),
        (TIPO_ACCESORIO, 'Accesorio'),
        (TIPO_SERVICIO, 'Servicio'),
    ]

    UNIDAD_ML = 'ml'
    UNIDAD_MG = 'mg'
    UNIDAD_G = 'g'
    UNIDAD_UNIDAD = 'unidad'
    UNIDAD_TABLETA = 'tableta'
    UNIDAD_CHOICES = [
        (UNIDAD_ML, 'ml'),
        (UNIDAD_MG, 'mg'),
        (UNIDAD_G, 'g'),
        (UNIDAD_UNIDAD, 'unidad'),
        (UNIDAD_TABLETA, 'tableta'),
    ]

    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_ACCESORIO)
    codigo = models.CharField(max_length=50, blank=True)
    presentacion = models.CharField(max_length=120, blank=True)
    contenido = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unidad_contenido = models.CharField(max_length=20, choices=UNIDAD_CHOICES, blank=True)
    lote = models.CharField(max_length=80, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=150, blank=True)
    stock_inicial = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=0)
    costo_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    descuento_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    descuento_desde = models.DateField(null=True, blank=True)
    descuento_hasta = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        permissions = [
            ('change_producto_stock', 'Puede ajustar stock de producto'),
            ('change_producto_precio', 'Puede cambiar precio de producto'),
            ('change_producto_costo', 'Puede cambiar costo de producto'),
            ('change_producto_lote', 'Puede cambiar lote/vencimiento de producto'),
        ]

    def __str__(self):
        return self.nombre

    def descuento_activo(self, date=None):
        if not self.descuento_pct or self.descuento_pct <= 0:
            return False
        today = date or timezone.localdate()
        if self.descuento_desde and today < self.descuento_desde:
            return False
        if self.descuento_hasta and today > self.descuento_hasta:
            return False
        return True


class TipoDescuento(models.Model):
    tipo = models.CharField(max_length=20, choices=Producto.TIPO_CHOICES, unique=True)
    descuento_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    descuento_desde = models.DateField(null=True, blank=True)
    descuento_hasta = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Descuento por tipo'
        verbose_name_plural = 'Descuentos por tipo'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.descuento_pct}%"

    def descuento_activo(self, date=None):
        if not self.descuento_pct or self.descuento_pct <= 0:
            return False
        today = date or timezone.localdate()
        if self.descuento_desde and today < self.descuento_desde:
            return False
        if self.descuento_hasta and today > self.descuento_hasta:
            return False
        return True


class ProductoLote(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='lotes')
    lote = models.CharField(max_length=80)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lote de producto'
        verbose_name_plural = 'Lotes de producto'
        ordering = ['fecha_vencimiento', 'created_at']
        unique_together = ('producto', 'lote', 'fecha_vencimiento')

    def __str__(self):
        return f"{self.producto.nombre} - {self.lote}"


class Venta(models.Model):
    METODO_EFECTIVO = 'EFECTIVO'
    METODO_TARJETA = 'TARJETA'
    METODO_TRANSFERENCIA = 'TRANSFERENCIA'
    METODO_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TARJETA, 'Tarjeta'),
        (METODO_TRANSFERENCIA, 'Transferencia'),
    ]

    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_PAGADA = 'PAGADA'
    ESTADO_ANULADA = 'ANULADA'
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_PAGADA, 'Pagada'),
        (ESTADO_ANULADA, 'Anulada'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    id_propietario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ventas_como_cliente')
    cliente_nombre = models.CharField(max_length=200, blank=True)
    vendedor = models.ForeignKey('usuarios.Staff', null=True, blank=True, on_delete=models.PROTECT, related_name='ventas')
    notas = models.TextField(blank=True)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES, default=METODO_EFECTIVO)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PAGADA)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ventas_creadas')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ventas_actualizadas')
    stock_committed = models.BooleanField(default=False)
    descuento_global = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    iva_rate_aplicado = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']

    def __str__(self):
        return f"Venta #{self.id} - {self.total}"

    def apply_stock_changes(self):
        """Apply stock decrements for this sale's items.

        Raises ValueError if any product doesn't have enough stock.
        Sets `stock_committed` to True once applied.
        """
        if self.stock_committed:
            return
        # Collect updates
        updates = []
        for item in self.items.select_related('producto').all():
            prod = item.producto
            if prod.tipo == Producto.TIPO_SERVICIO:
                continue
            if prod.tipo == Producto.TIPO_MEDICAMENTO:
                # Ensure at least one lot exists if stock is present
                if not prod.lotes.exists() and prod.stock_inicial > 0:
                    ProductoLote.objects.create(
                        producto=prod,
                        lote=prod.lote or 'SIN-LOTE',
                        fecha_vencimiento=prod.fecha_vencimiento,
                        cantidad=prod.stock_inicial,
                    )
                # Check lot availability (FEFO)
                available = prod.lotes.filter(cantidad__gt=0).order_by('fecha_vencimiento', 'created_at')
                total = sum(l.cantidad for l in available)
                if item.cantidad > total:
                    raise ValueError(f"Stock insuficiente para {prod.nombre}: {total} < {item.cantidad}")
            else:
                if item.cantidad > prod.stock_inicial:
                    raise ValueError(f"Stock insuficiente para {prod.nombre}: {prod.stock_inicial} < {item.cantidad}")
            updates.append((prod, item.cantidad, item))

        # Apply updates
        for prod, qty, item in updates:
            if prod.tipo == Producto.TIPO_MEDICAMENTO:
                remaining = qty
                used_lotes = []
                if item.lote:
                    lot = prod.lotes.filter(lote=item.lote).order_by('fecha_vencimiento').first()
                    if not lot or lot.cantidad < remaining:
                        raise ValueError(f"Stock insuficiente en lote {item.lote} para {prod.nombre}.")
                    used_lotes.append((lot, remaining))
                    remaining = 0
                else:
                    for lot in prod.lotes.filter(cantidad__gt=0).order_by('fecha_vencimiento', 'created_at'):
                        if remaining <= 0:
                            break
                        take = min(lot.cantidad, remaining)
                        used_lotes.append((lot, take))
                        remaining -= take
                # Apply lot deductions
                before_total = prod.stock_inicial
                for lot, take in used_lotes:
                    lot.cantidad -= take
                    lot.save(update_fields=['cantidad'])
                    InventoryMovement.objects.create(
                        producto=prod,
                        tipo=InventoryMovement.TIPO_VENTA,
                        cantidad=-take,
                        stock_before=before_total,
                        stock_after=before_total - take,
                        lote=lot.lote,
                        fecha_vencimiento=lot.fecha_vencimiento,
                        referencia=f"Venta #{self.id}",
                        created_by=self.updated_by or self.created_by,
                    )
                    before_total -= take
                prod.stock_inicial = sum(l.cantidad for l in prod.lotes.all())
                prod.save(update_fields=['stock_inicial'])
                if used_lotes:
                    if len(used_lotes) == 1:
                        item.lote = used_lotes[0][0].lote
                    else:
                        item.lote = 'MULTI'
                    item.save(update_fields=['lote'])
            else:
                before = prod.stock_inicial
                prod.stock_inicial = before - qty
                prod.save(update_fields=['stock_inicial'])
                InventoryMovement.objects.create(
                    producto=prod,
                    tipo=InventoryMovement.TIPO_VENTA,
                    cantidad=-qty,
                    stock_before=before,
                    stock_after=prod.stock_inicial,
                    lote=item.lote or prod.lote,
                    fecha_vencimiento=prod.fecha_vencimiento,
                    referencia=f"Venta #{self.id}",
                    created_by=self.updated_by or self.created_by,
                )

        self.stock_committed = True
        self.save(update_fields=['stock_committed'])

    def revert_stock_changes(self):
        """Revert stock decrements for this sale's items.

        Adds quantities back and sets `stock_committed` to False.
        """
        if not self.stock_committed:
            return
        movimientos = InventoryMovement.objects.filter(
            referencia=f"Venta #{self.id}",
            tipo=InventoryMovement.TIPO_VENTA
        ).select_related('producto')
        for mov in movimientos:
            prod = mov.producto
            if prod.tipo == Producto.TIPO_SERVICIO:
                continue
            before = prod.stock_inicial
            if prod.tipo == Producto.TIPO_MEDICAMENTO:
                lot, _ = ProductoLote.objects.get_or_create(
                    producto=prod,
                    lote=mov.lote or prod.lote,
                    fecha_vencimiento=mov.fecha_vencimiento or prod.fecha_vencimiento,
                    defaults={'cantidad': 0}
                )
                lot.cantidad += abs(mov.cantidad)
                lot.save(update_fields=['cantidad'])
                prod.stock_inicial = sum(l.cantidad for l in prod.lotes.all())
                prod.save(update_fields=['stock_inicial'])
                InventoryMovement.objects.create(
                    producto=prod,
                    tipo=InventoryMovement.TIPO_ANULACION,
                    cantidad=abs(mov.cantidad),
                    stock_before=before,
                    stock_after=prod.stock_inicial,
                    lote=lot.lote,
                    fecha_vencimiento=lot.fecha_vencimiento,
                    referencia=f"Anulacion venta #{self.id}",
                    created_by=self.updated_by or self.created_by,
                )
            else:
                prod.stock_inicial = before + abs(mov.cantidad)
                prod.save(update_fields=['stock_inicial'])
                InventoryMovement.objects.create(
                    producto=prod,
                    tipo=InventoryMovement.TIPO_ANULACION,
                    cantidad=abs(mov.cantidad),
                    stock_before=before,
                    stock_after=prod.stock_inicial,
                    lote=mov.lote or prod.lote,
                    fecha_vencimiento=prod.fecha_vencimiento,
                    referencia=f"Anulacion venta #{self.id}",
                    created_by=self.updated_by or self.created_by,
                )

        self.stock_committed = False
        self.save(update_fields=['stock_committed'])


class VentaConfig(models.Model):
    IVA_0 = '0'
    IVA_15 = '0.15'
    IVA_CHOICES = [
        (IVA_0, '0%'),
        (IVA_15, '15%'),
    ]

    descuento_habilitado = models.BooleanField(default=False)
    iva_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0.15, choices=IVA_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ConfiguraciÃ³n de ventas'
        verbose_name_plural = 'ConfiguraciÃ³n de ventas'

    def __str__(self):
        return 'ConfiguraciÃ³n de ventas'


def get_venta_config():
    config, _ = VentaConfig.objects.get_or_create(
        pk=1,
        defaults={'descuento_habilitado': False, 'iva_rate': 0.15},
    )
    return config
class SaleItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='sale_items')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    lote = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name = 'Item de Venta'
        verbose_name_plural = 'Items de Venta'

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad} @ {self.precio_unitario}"

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - (self.descuento or 0)

    def save(self, *args, **kwargs):
        if (self.costo_unitario is None or self.costo_unitario == 0) and self.producto_id:
            self.costo_unitario = self.producto.costo_compra or 0
        return super().save(*args, **kwargs)


class VentaAudit(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='audits')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)  # created, updated, deleted
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Audit Venta'
        verbose_name_plural = 'Auditoría Ventas'

    def __str__(self):
        return f"{self.action} by {self.user} on {self.timestamp}"


class SolicitudAnulacionVenta(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_APROBADA = 'APROBADA'
    ESTADO_RECHAZADA = 'RECHAZADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='anulaciones')
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitud de AnulaciÃ³n'
        verbose_name_plural = 'Solicitudes de AnulaciÃ³n'
        ordering = ['-created_at']

    def __str__(self):
        return f"Solicitud anulaciÃ³n venta #{self.venta_id} ({self.estado})"


class Recordatorio(models.Model):
    TIPO_ENTRADA = 'ENTRADA'
    TIPO_PROVEEDOR = 'PROVEEDOR'
    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada de producto'),
        (TIPO_PROVEEDOR, 'Visita de proveedor'),
    ]

    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_COMPLETADO = 'COMPLETADO'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_COMPLETADO, 'Completado'),
    ]

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha = models.DateTimeField()
    proveedor = models.CharField(max_length=200, blank=True)
    producto = models.ForeignKey(Producto, null=True, blank=True, on_delete=models.SET_NULL, related_name='recordatorios')
    cantidad = models.PositiveIntegerField(null=True, blank=True)
    notas = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Recordatorio'
        verbose_name_plural = 'Recordatorios'
        ordering = ['fecha']

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"


class InventoryMovement(models.Model):
    TIPO_ENTRADA = 'ENTRADA'
    TIPO_SALIDA = 'SALIDA'
    TIPO_AJUSTE = 'AJUSTE'
    TIPO_VENTA = 'VENTA'
    TIPO_ANULACION = 'ANULACION'
    TIPO_RESERVA = 'RESERVA'
    TIPO_LIBERACION = 'LIBERACION'
    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SALIDA, 'Salida'),
        (TIPO_AJUSTE, 'Ajuste'),
        (TIPO_VENTA, 'Venta'),
        (TIPO_ANULACION, 'Anulación'),
        (TIPO_RESERVA, 'Reserva'),
        (TIPO_LIBERACION, 'Liberación'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    stock_before = models.IntegerField(default=0)
    stock_after = models.IntegerField(default=0)
    lote = models.CharField(max_length=80, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    referencia = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.producto} {self.tipo} {self.cantidad}"


class StockAdjustmentRequest(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_APROBADA = 'APROBADA'
    ESTADO_RECHAZADA = 'RECHAZADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='ajustes')
    cantidad = models.IntegerField(help_text='Use positivo para entrada y negativo para salida.')
    motivo = models.TextField(blank=True)
    lote = models.CharField(max_length=80, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ajustes_solicitados')
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ajustes_aprobados')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitud de ajuste'
        verbose_name_plural = 'Solicitudes de ajuste'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ajuste {self.producto} {self.cantidad} ({self.estado})"


def recalc_venta_total(instance):
    subtotal = Decimal('0')
    for item in instance.items.all():
        subtotal += Decimal(str(item.subtotal or 0))
    descuento = Decimal(str(instance.descuento_global or 0))
    total = subtotal - descuento
    if total < 0:
        total = Decimal('0')
    rate = Decimal(str(instance.iva_rate_aplicado)) if instance.iva_rate_aplicado is not None else Decimal(str(get_venta_config().iva_rate or 0))
    if rate > 0:
        base_sin_iva = (total / (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        impuesto = (total - base_sin_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        impuesto = Decimal('0.00')
    instance.total = total
    instance.impuesto = impuesto
    instance.save(update_fields=['total', 'impuesto'])
