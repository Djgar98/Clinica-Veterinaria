from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from .models import AccessLog, AuditLog, Notification
from .security import is_locked_out, register_login_attempt, get_client_ip

from .forms import UserCreateForm, UserUpdateForm
from .roles import ROLE_CHOICES, set_user_roles, ROLE_DUENO, get_user_roles


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = get_user_model()
    template_name = 'usuarios/user_list.html'
    context_object_name = 'users'
    permission_required = 'auth.view_user'

    def get_queryset(self):
        return self.model.objects.all().order_by('username')


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    form_class = UserCreateForm
    template_name = 'usuarios/user_form.html'
    success_url = reverse_lazy('usuarios:list')
    permission_required = 'auth.add_user'


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = get_user_model()
    form_class = UserUpdateForm
    template_name = 'usuarios/user_form.html'
    success_url = reverse_lazy('usuarios:list')
    permission_required = 'auth.change_user'


class UserBulkRoleView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'usuarios/user_bulk_roles.html'
    permission_required = 'auth.change_user'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        users = get_user_model().objects.all().order_by('username')
        ctx['users'] = [{
            'id': u.id,
            'username': u.username,
            'full_name': u.get_full_name() or '—',
            'roles': list(get_user_roles(u)) or [ROLE_DUENO],
        } for u in users]
        ctx['role_choices'] = ROLE_CHOICES
        return ctx

    def post(self, request, *args, **kwargs):
        users = get_user_model().objects.all()
        for user in users:
            roles = request.POST.getlist(f'roles_{user.id}')
            roles = [r for r in roles if r in dict(ROLE_CHOICES)]
            if not roles:
                roles = [ROLE_DUENO]
            set_user_roles(user, roles=roles)
        return redirect('usuarios:list')


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            username = (request.POST.get('username') or '').strip()
            ip = get_client_ip(request)
            if is_locked_out(username, ip):
                form = self.get_form()
                form.add_error(None, 'Demasiados intentos fallidos. Intenta de nuevo en unos minutos.')
                return self.form_invalid(form)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        username = (form.cleaned_data.get('username') or '').strip()
        register_login_attempt(self.request, username, True)
        return super().form_valid(form)

    def form_invalid(self, form):
        username = (self.request.POST.get('username') or '').strip()
        register_login_attempt(self.request, username, False)
        return super().form_invalid(form)


class AccessLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = AccessLog
    template_name = 'usuarios/access_log_list.html'
    context_object_name = 'logs'
    paginate_by = 50
    permission_required = 'usuarios.view_accesslog'

    def get_queryset(self):
        qs = AccessLog.objects.select_related('user').all()
        user = self.request.GET.get('user')
        path = self.request.GET.get('path')
        status = self.request.GET.get('status')
        if user:
            qs = qs.filter(user__username__icontains=user)
        if path:
            qs = qs.filter(path__icontains=path)
        if status:
            qs = qs.filter(status_code=status)
        return qs


class AuditLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = AuditLog
    template_name = 'usuarios/audit_log_list.html'
    context_object_name = 'audits'
    paginate_by = 50
    permission_required = 'usuarios.view_auditlog'

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user', 'content_type').all()
        model = self.request.GET.get('model')
        user = self.request.GET.get('user')
        action = self.request.GET.get('action')
        if model:
            qs = qs.filter(model_label__icontains=model)
        if user:
            qs = qs.filter(user__username__icontains=user)
        if action:
            qs = qs.filter(action=action)
        return qs


def notifications_mark_read(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=401)
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return JsonResponse({'ok': True})
