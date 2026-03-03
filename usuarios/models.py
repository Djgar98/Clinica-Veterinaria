from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

# Aquí puedes extender el modelo de usuario o añadir perfiles de veterinarios/propietarios.


class Perfil(models.Model):
    nombre = models.CharField(max_length=150)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.nombre


class Personal(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal')
    puesto = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    es_veterinario = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Personal'
        verbose_name_plural = 'Personal'

    def __str__(self):
        return getattr(self.user, 'get_full_name', lambda: str(self.user))() or str(self.user)


class Staff(models.Model):
    CARGO_CHOICES = [
        ('VETERINARIO', 'Veterinario'),
        ('ADMIN', 'Administrador'),
        ('ASISTENTE', 'Asistente'),
        ('INVENTARIO', 'Inventario'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    nombre_completo = models.CharField(max_length=200)
    cargo = models.CharField(max_length=20, choices=CARGO_CHOICES)
    telefono = models.CharField(max_length=30, blank=True)
    documento = models.CharField(max_length=50, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'

    def __str__(self):
        return self.nombre_completo or str(self.user)


class OwnerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owner_profile')
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    documento = models.CharField(max_length=50, blank=True)
    contacto_emergencia = models.CharField(max_length=200, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=20, blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Propietario'
        verbose_name_plural = 'Propietarios'

    def __str__(self):
        return getattr(self.user, 'get_full_name', lambda: str(self.user))() or str(self.user)


class AccessLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    path = models.CharField(max_length=300)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField(default=200)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de acceso'
        verbose_name_plural = 'Logs de acceso'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} {self.method} {self.path} {self.status_code}"


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Intento de login'
        verbose_name_plural = 'Intentos de login'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} {self.success} {self.created_at}"


class AuditLog(models.Model):
    ACTION_CREATE = 'created'
    ACTION_UPDATE = 'updated'
    ACTION_DELETE = 'deleted'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Creado'),
        (ACTION_UPDATE, 'Actualizado'),
        (ACTION_DELETE, 'Eliminado'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    model_label = models.CharField(max_length=100, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Auditoría'
        verbose_name_plural = 'Auditorías'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.model_label} {self.action} {self.object_id}"


class Notification(models.Model):
    LEVEL_INFO = 'info'
    LEVEL_SUCCESS = 'success'
    LEVEL_WARNING = 'warning'
    LEVEL_CHOICES = [
        (LEVEL_INFO, 'Info'),
        (LEVEL_SUCCESS, 'Success'),
        (LEVEL_WARNING, 'Warning'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user})"



