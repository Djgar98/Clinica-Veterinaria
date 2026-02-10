from django.contrib import admin
from .models import Mascota, Expediente


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'raza', 'fecha_nacimiento', 'sexo', 'owner')
    search_fields = ('nombre', 'especie', 'raza')


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = ('mascota', 'creado')

from .models import Consulta, Cita, SolicitudCita, SolicitudReprogramacion, CitaReminder, ReservaLote


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'mascota', 'diagnostico', 'medico')
    list_filter = ('fecha', 'medico')
    search_fields = ('diagnostico', 'descripcion', 'mascota__nombre')


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'mascota', 'veterinario', 'estado')
    list_filter = ('estado', 'fecha', 'veterinario')
    search_fields = ('mascota__nombre', 'notas')


@admin.register(SolicitudCita)
class SolicitudCitaAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'mascota', 'solicitado_por', 'estado')
    list_filter = ('estado',)
    search_fields = ('mascota__nombre', 'motivo')


@admin.register(SolicitudReprogramacion)
class SolicitudReprogramacionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'cita', 'estado')
    list_filter = ('estado',)
    search_fields = ('descripcion',)


@admin.register(CitaReminder)
class CitaReminderAdmin(admin.ModelAdmin):
    list_display = ('programado_para', 'cita', 'canal', 'estado', 'destinatario')
    list_filter = ('canal', 'estado')
    search_fields = ('destinatario', 'cita__mascota__nombre')


@admin.register(ReservaLote)
class ReservaLoteAdmin(admin.ModelAdmin):
    list_display = ('expediente', 'lote', 'cantidad', 'estado', 'created_at')
    list_filter = ('estado',)
    search_fields = ('expediente__mascota__nombre', 'lote__lote')
