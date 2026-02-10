from django.contrib import admin
from django.urls import path, include
from usuarios.views import CustomLoginView
from .views import custom_400, custom_403, custom_404, custom_500

handler400 = custom_400
handler403 = custom_403
handler404 = custom_404
handler500 = custom_500

def _admin_has_permission(request):
    user = request.user
    if not user.is_active:
        return False
    return user.is_superuser or user.groups.filter(name='ADMIN').exists()

admin.site.has_permission = _admin_has_permission

urlpatterns = [
    path('admin/', admin.site.urls),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('', include('clinica.urls', namespace='clinica')),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
]
