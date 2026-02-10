from django.contrib import admin
from .models import Categoria, Producto, Venta, Recordatorio, SolicitudAnulacionVenta, InventoryMovement, StockAdjustmentRequest, ProductoLote, VentaConfig


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'costo_compra', 'precio', 'stock_inicial', 'is_active')
    list_filter = ('categoria', 'is_active')
    search_fields = ('nombre', 'descripcion')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'total', 'id_propietario', 'vendedor')
    list_filter = ('fecha', 'vendedor')
    search_fields = ('notas', 'id_propietario__username', 'vendedor__nombre_completo')


@admin.register(Recordatorio)
class RecordatorioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'fecha', 'estado', 'producto', 'proveedor')
    list_filter = ('tipo', 'estado')
    search_fields = ('titulo', 'proveedor', 'producto__nombre')


@admin.register(SolicitudAnulacionVenta)
class SolicitudAnulacionVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'estado', 'solicitado_por', 'created_at')
    list_filter = ('estado',)
    search_fields = ('venta__id', 'solicitado_por__username', 'solicitado_por__first_name', 'solicitado_por__last_name')


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'stock_before', 'stock_after', 'created_at')
    list_filter = ('tipo',)
    search_fields = ('producto__nombre', 'referencia')


@admin.register(StockAdjustmentRequest)
class StockAdjustmentRequestAdmin(admin.ModelAdmin):
    list_display = ('producto', 'cantidad', 'estado', 'solicitado_por', 'created_at')
    list_filter = ('estado',)
    search_fields = ('producto__nombre', 'solicitado_por__username')


@admin.register(ProductoLote)
class ProductoLoteAdmin(admin.ModelAdmin):
    list_display = ('producto', 'lote', 'fecha_vencimiento', 'cantidad')
    list_filter = ('producto',)
    search_fields = ('producto__nombre', 'lote')


@admin.register(VentaConfig)
class VentaConfigAdmin(admin.ModelAdmin):
    list_display = ('descuento_habilitado', 'iva_rate', 'updated_at')

