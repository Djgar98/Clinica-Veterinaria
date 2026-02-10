from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserBulkRoleView,
    AccessLogListView, AuditLogListView, notifications_mark_read,
)

app_name = 'usuarios'

urlpatterns = [
    path('', UserListView.as_view(), name='list'),
    path('nuevo/', UserCreateView.as_view(), name='create'),
    path('<int:pk>/editar/', UserUpdateView.as_view(), name='edit'),
    path('roles/', UserBulkRoleView.as_view(), name='bulk_roles'),
    path('accesos/', AccessLogListView.as_view(), name='access_logs'),
    path('auditoria/', AuditLogListView.as_view(), name='audit_logs'),
    path('notifications/mark-read/', notifications_mark_read, name='notifications_mark_read'),
]
