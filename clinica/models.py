from django.db import models
from django.conf import settings
from django.utils import timezone


class Mascota(models.Model):
    SEXO_CHOICES = [
        ('M', 'Macho'),
        ('H', 'Hembra'),
    ]
    TAMANIO_CHOICES = [
        ('PEQ', 'Pequeño'),
        ('MED', 'Mediano'),
        ('GRA', 'Grande'),
    ]

    nombre = models.CharField(max_length=120)
    especie = models.CharField(max_length=60)
    raza = models.CharField(max_length=80, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    color = models.CharField(max_length=80, blank=True)
    tamanio = models.CharField(max_length=3, choices=TAMANIO_CHOICES, blank=True)
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    esterilizado = models.BooleanField(default=False)
    microchip = models.CharField(max_length=50, blank=True)
    alergias = models.TextField(blank=True)
    vacunas = models.TextField(blank=True)
    senas_particulares = models.TextField(blank=True)
    notas = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='mascotas')

    class Meta:
        verbose_name = 'Mascota'
        verbose_name_plural = 'Mascotas'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.especie})"


class Expediente(models.Model):
    mascota = models.OneToOneField(Mascota, on_delete=models.CASCADE, related_name='expediente')
    creado = models.DateTimeField(auto_now_add=True)
    historial = models.TextField(blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Expediente'
        verbose_name_plural = 'Expedientes'
        ordering = ['-creado']

    def __str__(self):
        return f"Expediente de {self.mascota.nombre}"


class Cita(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_CONFIRMADA = 'CONFIRMADA'
    ESTADO_REPROGRAMADA = 'REPROGRAMADA'
    ESTADO_ATENDIDA = 'ATENDIDA'
    ESTADO_CANCELADA = 'CANCELADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Por confirmar'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_REPROGRAMADA, 'Reprogramada'),
        (ESTADO_ATENDIDA, 'Atendida'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    ORIGEN_DIRECTA = 'DIRECTA'
    ORIGEN_SOLICITUD = 'SOLICITUD'
    ORIGEN_CHOICES = [
        (ORIGEN_DIRECTA, 'Directa'),
        (ORIGEN_SOLICITUD, 'Solicitud'),
    ]

    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='citas')
    fecha = models.DateTimeField(default=timezone.now)
    veterinario = models.ForeignKey('usuarios.Staff', null=True, blank=True, on_delete=models.PROTECT, related_name='citas')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default=ORIGEN_DIRECTA)
    notas = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['fecha']

    def __str__(self):
        return f"Cita {self.mascota.nombre} - {self.fecha:%Y-%m-%d %H:%M}"


class SolicitudCita(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_ATENDIDA = 'ATENDIDA'
    ESTADO_RECHAZADA = 'RECHAZADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ATENDIDA, 'Atendida'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='solicitudes_cita')
    cita_asignada = models.ForeignKey('Cita', null=True, blank=True, on_delete=models.SET_NULL, related_name='solicitudes_origen')
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_preferida = models.DateTimeField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitud de cita'
        verbose_name_plural = 'Solicitudes de cita'
        ordering = ['-created_at']

    def __str__(self):
        return f"Solicitud {self.mascota.nombre} - {self.get_estado_display()}"


class SolicitudReprogramacion(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_APROBADA = 'APROBADA'
    ESTADO_RECHAZADA = 'RECHAZADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='reprogramaciones')
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    nueva_fecha = models.DateTimeField()
    descripcion = models.TextField()
    motivo_rechazo = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Solicitud de reprogramación'
        verbose_name_plural = 'Solicitudes de reprogramación'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reprogramación {self.cita_id} - {self.get_estado_display()}"


class CitaReminder(models.Model):
    CANAL_WHATSAPP = 'WHATSAPP'
    CANAL_CHOICES = [
        (CANAL_WHATSAPP, 'WhatsApp'),
    ]

    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_ENVIADO = 'ENVIADO'
    ESTADO_FALLIDO = 'FALLIDO'
    ESTADO_OMITIDO = 'OMITIDO'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ENVIADO, 'Enviado'),
        (ESTADO_FALLIDO, 'Fallido'),
        (ESTADO_OMITIDO, 'Omitido'),
    ]

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='recordatorios')
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    programado_para = models.DateTimeField()
    enviado_en = models.DateTimeField(null=True, blank=True)
    destinatario = models.CharField(max_length=200, blank=True)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recordatorio de cita'
        verbose_name_plural = 'Recordatorios de citas'
        ordering = ['-programado_para']

    def __str__(self):
        return f"{self.cita_id} {self.canal} {self.estado}"


class Consulta(models.Model):
    ESTADO_ABIERTA = 'ABIERTA'
    ESTADO_CERRADA = 'CERRADA'
    ESTADO_CHOICES = [
        (ESTADO_ABIERTA, 'Abierta'),
        (ESTADO_CERRADA, 'Cerrada'),
    ]

    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='consultas')
    cita = models.ForeignKey(Cita, null=True, blank=True, on_delete=models.SET_NULL, related_name='consultas')
    fecha = models.DateTimeField(default=timezone.now)
    diagnostico = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    medico = models.ForeignKey('usuarios.Staff', null=True, blank=True, on_delete=models.SET_NULL, related_name='consultas')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ABIERTA)
    cerrada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Consulta'
        verbose_name_plural = 'Consultas'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha.date()} - {self.diagnostico} ({self.mascota.nombre})"


class Receta(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_ACEPTADA = 'ACEPTADA'
    ESTADO_RECHAZADA = 'RECHAZADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ACEPTADA, 'Aceptada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    consulta = models.OneToOneField(Consulta, on_delete=models.CASCADE, related_name='receta')
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='recetas')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    venta = models.ForeignKey('inventario.Venta', null=True, blank=True, on_delete=models.SET_NULL, related_name='recetas')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'
        ordering = ['-created_at']

    def __str__(self):
        return f"Receta #{self.id} - {self.mascota.nombre}"


class RecetaItem(models.Model):
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT, related_name='receta_items')
    cantidad = models.PositiveIntegerField(default=1)
    lote = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name = 'Item de receta'
        verbose_name_plural = 'Items de receta'

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class ReservaLote(models.Model):
    ESTADO_RESERVADO = 'RESERVADO'
    ESTADO_USADO = 'USADO'
    ESTADO_CANCELADO = 'CANCELADO'
    ESTADO_CHOICES = [
        (ESTADO_RESERVADO, 'Reservado'),
        (ESTADO_USADO, 'Usado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    expediente = models.ForeignKey('Expediente', on_delete=models.CASCADE, related_name='reservas_lote')
    consulta = models.ForeignKey('Consulta', null=True, blank=True, on_delete=models.SET_NULL, related_name='reservas_lote')
    lote = models.ForeignKey('inventario.ProductoLote', on_delete=models.PROTECT, related_name='reservas')
    venta = models.ForeignKey('inventario.Venta', null=True, blank=True, on_delete=models.SET_NULL, related_name='reservas_lote')
    cantidad = models.PositiveIntegerField(default=1)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_RESERVADO)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva de lote'
        verbose_name_plural = 'Reservas de lote'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reserva {self.lote} x{self.cantidad}"


class CitaEvent(models.Model):
    TIPO_CREADA = 'CREADA'
    TIPO_CONFIRMADA = 'CONFIRMADA'
    TIPO_CANCELADA = 'CANCELADA'
    TIPO_REPROG_SOLICITADA = 'REPROG_SOLICITADA'
    TIPO_REPROG_APROBADA = 'REPROG_APROBADA'
    TIPO_REPROG_RECHAZADA = 'REPROG_RECHAZADA'
    TIPO_ATENDIDA = 'ATENDIDA'
    TIPO_ORIGEN_SOLICITUD = 'ORIGEN_SOLICITUD'
    TIPO_ORIGEN_DIRECTA = 'ORIGEN_DIRECTA'
    TIPO_CHOICES = [
        (TIPO_CREADA, 'Creada'),
        (TIPO_CONFIRMADA, 'Confirmada'),
        (TIPO_CANCELADA, 'Cancelada'),
        (TIPO_REPROG_SOLICITADA, 'Reprogramación solicitada'),
        (TIPO_REPROG_APROBADA, 'Reprogramación aprobada'),
        (TIPO_REPROG_RECHAZADA, 'Reprogramación rechazada'),
        (TIPO_ATENDIDA, 'Atendida'),
        (TIPO_ORIGEN_SOLICITUD, 'Origen: solicitud'),
        (TIPO_ORIGEN_DIRECTA, 'Origen: directa'),
    ]

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='historial')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    detalle = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historial de cita'
        verbose_name_plural = 'Historial de citas'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cita_id} {self.tipo} {self.created_at:%Y-%m-%d %H:%M}"
