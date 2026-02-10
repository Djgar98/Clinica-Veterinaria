from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.urls import reverse

from usuarios.audit import log_action, compute_changes
from usuarios.notifications import notify_users
from usuarios.roles import has_role, ROLE_ADMIN, ROLE_ASISTENTE
from .models import Mascota, Expediente, Cita, SolicitudCita, SolicitudReprogramacion, Consulta, ReservaLote


def _attach_old_instance(sender, instance):
    if instance.pk:
        try:
            instance._old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None


@receiver(pre_save, sender=Mascota)
@receiver(pre_save, sender=Expediente)
@receiver(pre_save, sender=Cita)
@receiver(pre_save, sender=SolicitudCita)
@receiver(pre_save, sender=SolicitudReprogramacion)
@receiver(pre_save, sender=Consulta)
@receiver(pre_save, sender=ReservaLote)
def _pre_save(sender, instance, **kwargs):
    _attach_old_instance(sender, instance)


@receiver(post_save, sender=Mascota)
@receiver(post_save, sender=Expediente)
@receiver(post_save, sender=Cita)
@receiver(post_save, sender=SolicitudCita)
@receiver(post_save, sender=SolicitudReprogramacion)
@receiver(post_save, sender=Consulta)
@receiver(post_save, sender=ReservaLote)
def _post_save(sender, instance, created, **kwargs):
    if created:
        log_action(instance, 'created')
        return
    changes = compute_changes(instance, getattr(instance, '_old_instance', None))
    if changes:
        log_action(instance, 'updated', changes=changes)


@receiver(post_delete, sender=Mascota)
@receiver(post_delete, sender=Expediente)
@receiver(post_delete, sender=Cita)
@receiver(post_delete, sender=SolicitudCita)
@receiver(post_delete, sender=SolicitudReprogramacion)
@receiver(post_delete, sender=Consulta)
@receiver(post_delete, sender=ReservaLote)
def _post_delete(sender, instance, **kwargs):
    log_action(instance, 'deleted')


def _admin_asistentes():
    User = get_user_model()
    return list(User.objects.filter(
        Q(groups__name__in=['ADMIN', 'ASISTENTE']) | Q(is_superuser=True),
        is_active=True
    ).distinct())


@receiver(post_save, sender=SolicitudCita)
def _notify_solicitud_cita(sender, instance, created, **kwargs):
    if created:
        recipients = _admin_asistentes()
        title = 'Nueva solicitud de cita'
        message = f"{instance.mascota.nombre} — {instance.solicitado_por.get_full_name() if instance.solicitado_por else 'Sin solicitante'}"
        notify_users(recipients, title, message, url=reverse('clinica:solicitud_cita_list'), level='info')
        return
    old = getattr(instance, '_old_instance', None)
    if old and old.estado != instance.estado and instance.estado in [SolicitudCita.ESTADO_ATENDIDA, SolicitudCita.ESTADO_RECHAZADA]:
        recipients = []
        if instance.solicitado_por:
            recipients.append(instance.solicitado_por)
        if instance.cita_asignada and instance.cita_asignada.veterinario and instance.cita_asignada.veterinario.user:
            recipients.append(instance.cita_asignada.veterinario.user)
        title = 'Solicitud de cita atendida' if instance.estado == SolicitudCita.ESTADO_ATENDIDA else 'Solicitud de cita rechazada'
        message = f"{instance.mascota.nombre}"
        url = reverse('clinica:cita_detail', args=[instance.cita_asignada.id]) if instance.cita_asignada else reverse('clinica:solicitud_cita_list')
        notify_users(recipients, title, message, url=url, level='success' if instance.estado == SolicitudCita.ESTADO_ATENDIDA else 'warning')


@receiver(post_save, sender=SolicitudReprogramacion)
def _notify_solicitud_reprogramacion(sender, instance, created, **kwargs):
    if created:
        recipients = _admin_asistentes()
        title = 'Nueva solicitud de reprogramación'
        message = f"{instance.cita.mascota.nombre} — {instance.solicitado_por.get_full_name() if instance.solicitado_por else 'Sin solicitante'}"
        notify_users(recipients, title, message, url=reverse('clinica:solicitud_reprogramacion_list'), level='info')
        return
    old = getattr(instance, '_old_instance', None)
    if old and old.estado != instance.estado and instance.estado in [SolicitudReprogramacion.ESTADO_APROBADA, SolicitudReprogramacion.ESTADO_RECHAZADA]:
        recipients = []
        if instance.cita and instance.cita.mascota and instance.cita.mascota.owner:
            recipients.append(instance.cita.mascota.owner)
        if instance.cita and instance.cita.veterinario and instance.cita.veterinario.user:
            recipients.append(instance.cita.veterinario.user)
        title = 'Reprogramación aprobada' if instance.estado == SolicitudReprogramacion.ESTADO_APROBADA else 'Reprogramación rechazada'
        message = f"{instance.cita.mascota.nombre}"
        url = reverse('clinica:cita_detail', args=[instance.cita.id])
        notify_users(recipients, title, message, url=url, level='success' if instance.estado == SolicitudReprogramacion.ESTADO_APROBADA else 'warning')


@receiver(post_save, sender=Cita)
def _notify_cita_creada(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.origen != Cita.ORIGEN_DIRECTA:
        return
    if instance.created_by and not (has_role(instance.created_by, ROLE_ADMIN) or has_role(instance.created_by, ROLE_ASISTENTE) or instance.created_by.is_superuser):
        return
    recipients = []
    if instance.mascota and instance.mascota.owner:
        recipients.append(instance.mascota.owner)
    if instance.veterinario and instance.veterinario.user:
        recipients.append(instance.veterinario.user)
    if not recipients:
        return
    title = 'Cita creada'
    message = f"{instance.mascota.nombre} — {instance.fecha:%d %b %Y %H:%M}"
    url = reverse('clinica:cita_detail', args=[instance.id])
    notify_users(recipients, title, message, url=url, level='success')
