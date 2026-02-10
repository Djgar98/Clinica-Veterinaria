import json
from datetime import timedelta
from urllib import request as urlrequest

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from clinica.models import Cita, CitaReminder


class Command(BaseCommand):
    help = 'Envía recordatorios de citas por email y WhatsApp (si está configurado).'

    def handle(self, *args, **options):
        hours = getattr(settings, 'REMINDER_HOURS_BEFORE', 24)
        window = getattr(settings, 'REMINDER_SEND_WINDOW_MINUTES', 30)
        now = timezone.now()
        start = now + timedelta(hours=hours)
        end = start + timedelta(minutes=window)

        citas = Cita.objects.select_related('mascota', 'veterinario', 'mascota__owner').filter(
            fecha__gte=start,
            fecha__lte=end,
            estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_REPROGRAMADA]
        )

        total_sent = 0
        for cita in citas:
            total_sent += self._send_whatsapp(cita, start)

        self.stdout.write(self.style.SUCCESS(f'Recordatorios procesados. Enviados: {total_sent}'))

    def _already_sent(self, cita, canal):
        return CitaReminder.objects.filter(
            cita=cita,
            canal=canal,
            estado=CitaReminder.ESTADO_ENVIADO
        ).exists()

    def _get_phone(self, user):
        if not user:
            return ''
        personal = getattr(user, 'personal', None)
        if personal and getattr(personal, 'telefono', ''):
            return personal.telefono
        return ''

    def _send_whatsapp(self, cita, schedule_time):
        if self._already_sent(cita, CitaReminder.CANAL_WHATSAPP):
            return 0
        webhook = getattr(settings, 'WHATSAPP_WEBHOOK_URL', '')
        if not webhook:
            CitaReminder.objects.create(
                cita=cita,
                canal=CitaReminder.CANAL_WHATSAPP,
                estado=CitaReminder.ESTADO_OMITIDO,
                programado_para=schedule_time,
                destinatario='',
                error='Webhook no configurado'
            )
            return 0

        owner = getattr(cita.mascota, 'owner', None)
        phone_owner = self._get_phone(owner)
        vet = getattr(cita, 'veterinario', None)
        phone_vet = self._get_phone(getattr(vet, 'user', None))
        phones = [p for p in [phone_owner, phone_vet] if p]

        if not phones:
            CitaReminder.objects.create(
                cita=cita,
                canal=CitaReminder.CANAL_WHATSAPP,
                estado=CitaReminder.ESTADO_OMITIDO,
                programado_para=schedule_time,
                destinatario='',
                error='Sin teléfono disponible'
            )
            return 0

        message = (
            f"Recordatorio de cita: {cita.mascota.nombre} "
            f"{timezone.localtime(cita.fecha).strftime('%Y-%m-%d %H:%M')} "
            f"con {cita.veterinario.nombre_completo if cita.veterinario else 'la clínica'}."
        )

        payload = {
            'phones': phones,
            'message': message,
            'cita_id': cita.id,
        }
        token = getattr(settings, 'WHATSAPP_WEBHOOK_TOKEN', '')
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            req = urlrequest.Request(webhook, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            urlrequest.urlopen(req, timeout=10)
            CitaReminder.objects.create(
                cita=cita,
                canal=CitaReminder.CANAL_WHATSAPP,
                estado=CitaReminder.ESTADO_ENVIADO,
                programado_para=schedule_time,
                enviado_en=timezone.now(),
                destinatario=', '.join(phones),
            )
            return 1
        except Exception as exc:
            CitaReminder.objects.create(
                cita=cita,
                canal=CitaReminder.CANAL_WHATSAPP,
                estado=CitaReminder.ESTADO_FALLIDO,
                programado_para=schedule_time,
                destinatario=', '.join(phones),
                error=str(exc),
            )
            return 0
