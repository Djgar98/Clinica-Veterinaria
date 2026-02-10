from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from .models import LoginAttempt


def get_client_ip(request):
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def is_locked_out(username, ip):
    max_attempts = getattr(settings, 'LOGIN_LOCKOUT_MAX_ATTEMPTS', 5)
    window_minutes = getattr(settings, 'LOGIN_LOCKOUT_WINDOW_MINUTES', 15)
    block_minutes = getattr(settings, 'LOGIN_LOCKOUT_BLOCK_MINUTES', 15)
    if not username:
        return False
    window_start = timezone.now() - timedelta(minutes=window_minutes)
    attempts = LoginAttempt.objects.filter(
        username__iexact=username,
        ip_address=ip,
        success=False,
        created_at__gte=window_start,
    ).order_by('-created_at')
    if attempts.count() >= max_attempts:
        last = attempts.first()
        if last and last.created_at >= timezone.now() - timedelta(minutes=block_minutes):
            return True
    return False


def register_login_attempt(request, username, success):
    LoginAttempt.objects.create(
        username=username or '',
        ip_address=get_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:300] if request else '',
        success=bool(success),
    )
