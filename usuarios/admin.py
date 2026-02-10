from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import Perfil, Personal, Staff


User = get_user_model()

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Ensure "Es staff" defaults to False on create
        if obj is None and 'is_staff' in form.base_fields:
            form.base_fields['is_staff'].initial = False
        return form

    def save_model(self, request, obj, form, change):
        # Force is_staff to False on creation
        if not change:
            obj.is_staff = False
        super().save_model(request, obj, form, change)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'cargo', 'is_active', 'user')
    list_filter = ('cargo', 'is_active')
    search_fields = ('nombre_completo', 'user__username', 'user__email')


@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    list_display = ('user', 'puesto', 'telefono', 'es_veterinario')
    search_fields = ('user__username', 'user__email', 'puesto')


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email')
    search_fields = ('nombre', 'email')

