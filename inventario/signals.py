from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from usuarios.audit import log_action, compute_changes
from .models import (
    Producto, Venta, SaleItem, StockAdjustmentRequest,
    SolicitudAnulacionVenta, ProductoLote
)


def _attach_old_instance(sender, instance):
    if instance.pk:
        try:
            instance._old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None


@receiver(pre_save, sender=Producto)
@receiver(pre_save, sender=Venta)
@receiver(pre_save, sender=SaleItem)
@receiver(pre_save, sender=StockAdjustmentRequest)
@receiver(pre_save, sender=SolicitudAnulacionVenta)
@receiver(pre_save, sender=ProductoLote)
def _pre_save(sender, instance, **kwargs):
    _attach_old_instance(sender, instance)


@receiver(post_save, sender=Producto)
@receiver(post_save, sender=Venta)
@receiver(post_save, sender=SaleItem)
@receiver(post_save, sender=StockAdjustmentRequest)
@receiver(post_save, sender=SolicitudAnulacionVenta)
@receiver(post_save, sender=ProductoLote)
def _post_save(sender, instance, created, **kwargs):
    if created:
        log_action(instance, 'created')
        return
    changes = compute_changes(instance, getattr(instance, '_old_instance', None))
    if changes:
        log_action(instance, 'updated', changes=changes)


@receiver(post_delete, sender=Producto)
@receiver(post_delete, sender=Venta)
@receiver(post_delete, sender=SaleItem)
@receiver(post_delete, sender=StockAdjustmentRequest)
@receiver(post_delete, sender=SolicitudAnulacionVenta)
@receiver(post_delete, sender=ProductoLote)
def _post_delete(sender, instance, **kwargs):
    log_action(instance, 'deleted')
