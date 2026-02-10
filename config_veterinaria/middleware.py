from django.conf import settings
from django.shortcuts import render

from usuarios.threadlocals import set_current_request
from usuarios.security import get_client_ip
from usuarios.models import AccessLog


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Allow admin and login pages during maintenance
            path = request.path or ''
            if not path.startswith('/admin/') and not path.startswith('/accounts/'):
                if request.user.is_authenticated:
                    is_allowed_role = request.user.groups.filter(name__in=['ADMIN', 'ASISTENTE']).exists() or request.user.is_superuser
                else:
                    is_allowed_role = False
                if not is_allowed_role:
                    return render(request, '503.html', status=503)

        response = self.get_response(request)
        if response.status_code == 401:
            return render(request, '401.html', status=401)
        return response


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        return self.get_response(request)


class AccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            path = request.path or ''
            if path.startswith('/static/') or path.startswith('/media/'):
                return response
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                AccessLog.objects.create(
                    user=user,
                    path=path[:300],
                    method=(request.method or '')[:10],
                    status_code=response.status_code,
                    ip_address=get_client_ip(request),
                    user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:300],
                )
        except Exception:
            pass
        return response
