from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.urls import reverse
from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum, Count, F, DecimalField, ExpressionWrapper, OuterRef, Subquery
from django.db import transaction
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.http import HttpResponse, JsonResponse
import csv
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from .models import Mascota, Expediente, Consulta, Cita, SolicitudCita, SolicitudReprogramacion, CitaReminder, ReservaLote, CitaEvent, Receta, RecetaItem
from .forms import ConsultaForm, MascotaForm, CitaForm, SolicitudCitaForm, SolicitudReprogramacionForm, ReservaLoteForm, RecetaItemFormSet
from usuarios.models import Staff, AccessLog, AuditLog
from inventario.models import Venta, Producto, Recordatorio, SaleItem, InventoryMovement, ProductoLote, VentaAudit, StockAdjustmentRequest, SolicitudAnulacionVenta, TipoDescuento, get_venta_config, recalc_venta_total


def aplicar_reserva_lote(lote, qty, expediente, consulta, user):
    before = lote.producto.stock_inicial
    lote.cantidad -= qty
    lote.save(update_fields=['cantidad'])
    lote.producto.stock_inicial = sum(l.cantidad for l in lote.producto.lotes.all())
    lote.producto.save(update_fields=['stock_inicial'])
    reserva = ReservaLote.objects.create(
        expediente=expediente,
        consulta=consulta,
        lote=lote,
        cantidad=qty,
        estado=ReservaLote.ESTADO_RESERVADO,
        created_by=user if user and user.is_authenticated else None,
    )
    InventoryMovement.objects.create(
        producto=lote.producto,
        tipo=InventoryMovement.TIPO_RESERVA,
        cantidad=-qty,
        stock_before=before,
        stock_after=lote.producto.stock_inicial,
        lote=lote.lote,
        fecha_vencimiento=lote.fecha_vencimiento,
        referencia=f"Reserva #{reserva.id}" if reserva else 'Reserva',
        created_by=user if user and user.is_authenticated else None,
    )


def create_cita_reminders(cita, user=None):
    hours = getattr(settings, 'REMINDER_HOURS_BEFORE', 24)
    when = cita.fecha - timedelta(hours=hours)
    if when <= timezone.now():
        return 0
    created = 0
    for canal in [CitaReminder.CANAL_WHATSAPP]:
        exists = CitaReminder.objects.filter(
            cita=cita,
            canal=canal,
            estado=CitaReminder.ESTADO_PENDIENTE,
        ).exists()
        if exists:
            continue
        CitaReminder.objects.create(
            cita=cita,
            canal=canal,
            estado=CitaReminder.ESTADO_PENDIENTE,
            programado_para=when,
            destinatario='',
        )
        created += 1
    return created


def log_cita_event(cita, tipo, user=None, detalle=''):
    CitaEvent.objects.create(
        cita=cita,
        tipo=tipo,
        detalle=detalle or '',
        created_by=user if user and user.is_authenticated else None,
    )
from usuarios.roles import has_role, is_owner_only, get_user_role, ROLE_DUENO, ROLE_VETERINARIO, ROLE_ASISTENTE, ROLE_ADMIN, ROLE_INVENTARIO


def _get_tipo_descuentos_map():
    return {d.tipo: d for d in TipoDescuento.objects.all()}


def _get_descuento_pct_for_producto(prod, today, tipo_desc_map):
    if prod.descuento_activo(today):
        return Decimal(str(prod.descuento_pct or 0))
    tipo_desc = tipo_desc_map.get(prod.tipo)
    if tipo_desc and tipo_desc.descuento_activo(today):
        return Decimal(str(tipo_desc.descuento_pct or 0))
    return None


def create_venta_from_receta(receta, user, mark_paid=False):
    config = get_venta_config()
    rate = Decimal(str(config.iva_rate or 0))
    staff_profile = getattr(user, 'staff_profile', None) if user and user.is_authenticated else None
    owner = receta.mascota.owner
    venta = Venta.objects.create(
        id_propietario=owner,
        cliente_nombre=(owner.get_full_name() if owner else '') or (owner.username if owner else ''),
        vendedor=staff_profile,
        metodo_pago=Venta.METODO_EFECTIVO,
        estado=Venta.ESTADO_PAGADA if mark_paid else Venta.ESTADO_BORRADOR,
        notas=f"Venta generada desde receta #{receta.id}",
        created_by=user if user and user.is_authenticated else None,
        updated_by=user if user and user.is_authenticated else None,
        iva_rate_aplicado=rate,
    )
    today = timezone.localdate()
    tipo_desc_map = _get_tipo_descuentos_map()
    for item in receta.items.select_related('producto').all():
        prod = item.producto
        price_base = Decimal(str(prod.precio or 0))
        price_final = (price_base * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sale_item = SaleItem.objects.create(
            venta=venta,
            producto=prod,
            cantidad=item.cantidad,
            precio_unitario=price_final,
            lote=item.lote or '',
        )
        descuento_pct = _get_descuento_pct_for_producto(prod, today, tipo_desc_map)
        if descuento_pct and descuento_pct > 0:
            sale_item.descuento = (Decimal(item.cantidad) * price_final * descuento_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            sale_item.save(update_fields=['descuento'])
    if not config.descuento_habilitado:
        venta.descuento_global = Decimal('0')
        venta.save(update_fields=['descuento_global'])
    recalc_venta_total(venta)
    if mark_paid:
        venta.apply_stock_changes()
    VentaAudit.objects.create(
        venta=venta,
        user=user if user and user.is_authenticated else None,
        action='created',
        notes='Creación desde receta',
    )
    return venta


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'clinica/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        role = get_user_role(self.request.user)
        is_admin = has_role(self.request.user, ROLE_ADMIN) or self.request.user.is_superuser
        is_vet = has_role(self.request.user, ROLE_VETERINARIO)
        is_asistente = has_role(self.request.user, ROLE_ASISTENTE)
        is_inventario = has_role(self.request.user, ROLE_INVENTARIO)
        is_dueno = is_owner_only(self.request.user)
        now = timezone.now()

        upcoming_consultas = Consulta.objects.none()
        upcoming_citas = Cita.objects.none()
        if is_vet:
            staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
            if staff:
                upcoming_citas = Cita.objects.select_related('mascota', 'veterinario').filter(
                    veterinario=staff,
                    fecha__gte=now,
                    estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_REPROGRAMADA]
                ).order_by('fecha')[:10]
        elif is_asistente:
            upcoming_citas = Cita.objects.select_related('mascota', 'veterinario').filter(
                fecha__gte=now,
                estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_REPROGRAMADA]
            ).order_by('fecha')[:10]
        elif is_dueno:
            upcoming_citas = Cita.objects.select_related('mascota', 'veterinario').filter(
                mascota__owner=self.request.user,
                fecha__gte=now,
                estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_REPROGRAMADA]
            ).order_by('fecha')[:10]

        ctx['role'] = role
        ctx['is_admin'] = is_admin
        ctx['is_veterinario'] = is_vet
        ctx['is_asistente'] = is_asistente
        ctx['is_inventario'] = is_inventario
        ctx['is_dueno'] = is_dueno
        ctx['upcoming_consultas'] = upcoming_consultas
        ctx['upcoming_citas'] = upcoming_citas

        reminder_qs = CitaReminder.objects.filter(estado=CitaReminder.ESTADO_PENDIENTE)
        ctx['reminders_pending'] = reminder_qs.count()
        ctx['reminders_upcoming'] = reminder_qs.order_by('programado_para')[:5]

        if is_admin or is_inventario:
            limite = (timezone.now() + timedelta(days=30)).date()
            lotes_vencer = ProductoLote.objects.select_related('producto').filter(
                cantidad__gt=0,
                fecha_vencimiento__isnull=False,
                fecha_vencimiento__lte=limite,
                producto__is_active=True,
                producto__tipo=Producto.TIPO_MEDICAMENTO,
            ).order_by('fecha_vencimiento')[:5]
            ctx['lotes_por_vencer'] = lotes_vencer

        if is_dueno or is_vet or is_asistente:
            if is_dueno:
                ctx['solicitudes_pendientes'] = SolicitudCita.objects.filter(
                    estado=SolicitudCita.ESTADO_PENDIENTE,
                    solicitado_por=self.request.user
                ).count()
                ctx['solicitudes_pendientes_list'] = SolicitudCita.objects.filter(
                    estado=SolicitudCita.ESTADO_PENDIENTE,
                    solicitado_por=self.request.user
                ).order_by('-created_at')[:5]
                ctx['solicitudes_recientes'] = SolicitudCita.objects.filter(
                    solicitado_por=self.request.user
                ).select_related('cita_asignada', 'mascota').order_by('-created_at')[:5]
                latest_status = SolicitudCita.objects.filter(
                    solicitado_por=self.request.user
                ).exclude(
                    estado=SolicitudCita.ESTADO_PENDIENTE
                ).select_related('cita_asignada', 'mascota').order_by('-updated_at').first()
                ctx['solicitud_status_latest'] = latest_status
            if is_asistente:
                ctx['solicitudes_pendientes'] = SolicitudCita.objects.filter(estado=SolicitudCita.ESTADO_PENDIENTE).count()
                ctx['reprog_pendientes'] = SolicitudReprogramacion.objects.filter(estado=SolicitudReprogramacion.ESTADO_PENDIENTE).count()
                recordatorios = Recordatorio.objects.filter(
                    fecha__gte=now,
                    estado=Recordatorio.ESTADO_PENDIENTE
                ).order_by('fecha')[:5]
                ctx['recordatorios_proximos'] = recordatorios
            if is_vet:
                ctx['reprog_pendientes'] = SolicitudReprogramacion.objects.filter(
                    estado=SolicitudReprogramacion.ESTADO_PENDIENTE,
                    solicitado_por=self.request.user
                ).count()
                staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
                if staff:
                    ctx['citas_hoy_vet'] = Cita.objects.filter(
                        veterinario=staff,
                        fecha__date=timezone.localdate(),
                        estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_REPROGRAMADA]
                    ).count()
                    ctx['consultas_abiertas'] = Consulta.objects.filter(
                        medico=staff,
                        estado=Consulta.ESTADO_ABIERTA
                    ).count()
            return ctx

        today = timezone.localdate()

        if is_admin:
            month_start = today.replace(day=1)
            ventas_mes = Venta.objects.filter(
                fecha__date__gte=month_start,
                fecha__date__lte=today,
                estado=Venta.ESTADO_PAGADA
            )
            ventas_mes_stats = ventas_mes.aggregate(total=Sum('total'), cantidad=Count('id'))
            ctx['ventas_mes_total'] = ventas_mes_stats.get('total') or 0
            ctx['ventas_mes_count'] = ventas_mes_stats.get('cantidad') or 0
            ctx['anulaciones_pendientes'] = SolicitudAnulacionVenta.objects.filter(
                estado=SolicitudAnulacionVenta.ESTADO_PENDIENTE
            ).count()
            ctx['ajustes_pendientes'] = StockAdjustmentRequest.objects.filter(
                estado=StockAdjustmentRequest.ESTADO_PENDIENTE
            ).count()
            ctx['solicitudes_cita_pendientes'] = SolicitudCita.objects.filter(
                estado=SolicitudCita.ESTADO_PENDIENTE
            ).count()
            ctx['reprog_pendientes_admin'] = SolicitudReprogramacion.objects.filter(
                estado=SolicitudReprogramacion.ESTADO_PENDIENTE
            ).count()
            ctx['citas_hoy'] = Cita.objects.filter(fecha__date=today).count()
            ctx['ventas_recientes'] = Venta.objects.select_related('id_propietario', 'vendedor').order_by('-fecha')[:5]
            ctx['audit_recientes'] = AuditLog.objects.select_related('user').order_by('-created_at')[:8]
            ctx['access_hoy'] = AccessLog.objects.filter(created_at__date=today).count()
            ctx['audit_hoy'] = AuditLog.objects.filter(created_at__date=today).count()

        ventas_qs = Venta.objects.filter(fecha__date=today, estado=Venta.ESTADO_PAGADA)
        ventas_stats = ventas_qs.aggregate(
            total=Sum('total'),
            cantidad=Count('id')
        )
        stock_critico_qs = Producto.objects.filter(stock_inicial__lte=F('stock_minimo')).exclude(tipo=Producto.TIPO_SERVICIO)
        stock_critico = stock_critico_qs.order_by('stock_inicial')[:5]
        consultas_recientes = Consulta.objects.select_related('mascota', 'medico').order_by('-fecha')[:5]
        recordatorios = Recordatorio.objects.filter(
            fecha__gte=now,
            estado=Recordatorio.ESTADO_PENDIENTE
        ).order_by('fecha')[:5]

        ctx.update({
            'is_inventario_role': is_inventario,
            'ventas_hoy_total': ventas_stats.get('total') or 0,
            'ventas_hoy_count': ventas_stats.get('cantidad') or 0,
            'stock_critico': stock_critico,
            'stock_critico_count': stock_critico_qs.count(),
            'consultas_recientes': consultas_recientes,
            'recordatorios_proximos': recordatorios,
        })
        return ctx


class ReportesView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        is_admin = user.is_superuser or user.groups.filter(name='ADMIN').exists()
        if not is_admin:
            return redirect('clinica:dashboard')

        today = timezone.localdate()
        date_to = request.GET.get('to')
        date_from = request.GET.get('from')
        period = request.GET.get('period', 'day')

        if date_to:
            try:
                date_to = timezone.datetime.fromisoformat(date_to).date()
            except ValueError:
                date_to = today
        else:
            date_to = today

        if date_from:
            try:
                date_from = timezone.datetime.fromisoformat(date_from).date()
            except ValueError:
                date_from = date_to - timedelta(days=29)
        else:
            date_from = date_to - timedelta(days=29)

        ventas_qs = Venta.objects.filter(
            estado=Venta.ESTADO_PAGADA,
            fecha__date__gte=date_from,
            fecha__date__lte=date_to
        )

        if period == 'month':
            ventas_group = ventas_qs.annotate(period=TruncMonth('fecha')).values('period').annotate(
                total=Sum('total'),
                cantidad=Count('id')
            ).order_by('period')
        else:
            ventas_group = ventas_qs.annotate(period=TruncDate('fecha')).values('period').annotate(
                total=Sum('total'),
                cantidad=Count('id')
            ).order_by('period')

        base_items = SaleItem.objects.filter(
            venta__estado=Venta.ESTADO_PAGADA,
            venta__fecha__date__gte=date_from,
            venta__fecha__date__lte=date_to
        ).annotate(
            line_total=ExpressionWrapper(
                (F('cantidad') * F('precio_unitario')) - F('descuento'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            line_cost=ExpressionWrapper(
                (F('cantidad') * F('producto__costo_compra')),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            line_profit=ExpressionWrapper(
                (F('cantidad') * F('precio_unitario')) - F('descuento') - (F('cantidad') * F('producto__costo_compra')),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )

        top_productos = base_items.values('producto__nombre').annotate(
            cantidad=Sum('cantidad'),
            ingresos=Sum('line_total'),
            costo=Sum('line_cost'),
            utilidad=Sum('line_profit')
        ).order_by('-cantidad')[:10]

        top_categorias = base_items.values('producto__categoria__name').annotate(
            cantidad=Sum('cantidad'),
            ingresos=Sum('line_total'),
            costo=Sum('line_cost'),
            utilidad=Sum('line_profit')
        ).order_by('-ingresos')[:10]

        utilidad_total = base_items.aggregate(
            ingresos=Sum('line_total'),
            costo=Sum('line_cost'),
            utilidad=Sum('line_profit')
        )

        ventas_por_vendedor = ventas_qs.values('vendedor__nombre_completo').annotate(
            cantidad=Count('id'),
            total=Sum('total')
        ).order_by('-total')[:10]

        utilidad_por_vendedor = base_items.values('venta__vendedor__nombre_completo').annotate(
            ingresos=Sum('line_total'),
            costo=Sum('line_cost'),
            utilidad=Sum('line_profit')
        ).order_by('-utilidad')[:10]

        clientes_frecuentes = ventas_qs.filter(id_propietario__isnull=False).values(
            'id_propietario__first_name',
            'id_propietario__last_name',
            'id_propietario__username'
        ).annotate(
            cantidad=Count('id'),
            total=Sum('total')
        ).order_by('-cantidad')[:10]

        citas_qs = Cita.objects.filter(
            fecha__date__gte=date_from,
            fecha__date__lte=date_to
        )
        consultas_qs = Consulta.objects.filter(
            fecha__date__gte=date_from,
            fecha__date__lte=date_to
        )

        citas_group = citas_qs.annotate(period=TruncDate('fecha')).values('period').annotate(
            cantidad=Count('id')
        ).order_by('period')

        consultas_group = consultas_qs.annotate(period=TruncDate('fecha')).values('period').annotate(
            cantidad=Count('id')
        ).order_by('period')

        mascotas_frecuentes = consultas_qs.values(
            'mascota__nombre',
            'mascota__owner__first_name',
            'mascota__owner__last_name',
            'mascota__owner__username'
        ).annotate(
            cantidad=Count('id')
        ).order_by('-cantidad')[:10]

        stock_critico = Producto.objects.filter(
            stock_inicial__lte=F('stock_minimo'),
            is_active=True
        ).exclude(tipo=Producto.TIPO_SERVICIO).order_by('stock_inicial')[:10]

        context = {
            'date_from': date_from,
            'date_to': date_to,
            'period': period,
            'ventas_group': ventas_group,
            'top_productos': top_productos,
            'top_categorias': top_categorias,
            'ventas_por_vendedor': ventas_por_vendedor,
            'utilidad_por_vendedor': utilidad_por_vendedor,
            'clientes_frecuentes': clientes_frecuentes,
            'citas_group': citas_group,
            'consultas_group': consultas_group,
            'mascotas_frecuentes': mascotas_frecuentes,
            'stock_critico': stock_critico,
            'utilidad_total': utilidad_total,
            'ventas_series': list(ventas_group),
            'citas_series': list(citas_group),
            'consultas_series': list(consultas_group),
        }

        export = request.GET.get('export')
        if export in ('csv', 'excel'):
            resp = HttpResponse(content_type='text/csv')
            filename = f"reportes_{date_from}_{date_to}.csv"
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(resp)

            writer.writerow(['Reporte', 'Periodo', f'{date_from} a {date_to}'])
            writer.writerow([])

            writer.writerow(['Ventas por periodo'])
            writer.writerow(['Periodo', 'Cantidad', 'Total'])
            for row in ventas_group:
                writer.writerow([row['period'], row['cantidad'], f"C$ {row['total']}"])
            writer.writerow([])

            writer.writerow(['Top productos'])
            writer.writerow(['Producto', 'Cantidad', 'Ingresos', 'Costo', 'Utilidad'])
            for row in top_productos:
                writer.writerow([row['producto__nombre'], row['cantidad'], f"C$ {row['ingresos']}", f"C$ {row['costo']}", f"C$ {row['utilidad']}"])
            writer.writerow([])

            writer.writerow(['Ventas por categoría'])
            writer.writerow(['Categoría', 'Cantidad', 'Ingresos', 'Costo', 'Utilidad'])
            for row in top_categorias:
                writer.writerow([row['producto__categoria__name'], row['cantidad'], f"C$ {row['ingresos']}", f"C$ {row['costo']}", f"C$ {row['utilidad']}"])
            writer.writerow([])

            writer.writerow(['Ventas por vendedor'])
            writer.writerow(['Vendedor', 'Cantidad', 'Total'])
            for row in ventas_por_vendedor:
                writer.writerow([row['vendedor__nombre_completo'], row['cantidad'], f"C$ {row['total']}"])
            writer.writerow([])

            writer.writerow(['Utilidad por vendedor'])
            writer.writerow(['Vendedor', 'Ingresos', 'Costo', 'Utilidad'])
            for row in utilidad_por_vendedor:
                writer.writerow([row['venta__vendedor__nombre_completo'], f"C$ {row['ingresos']}", f"C$ {row['costo']}", f"C$ {row['utilidad']}"])
            writer.writerow([])

            writer.writerow(['Clientes frecuentes'])
            writer.writerow(['Cliente', 'Compras', 'Total'])
            for row in clientes_frecuentes:
                nombre = f"{row['id_propietario__first_name']} {row['id_propietario__last_name']}".strip()
                if not nombre:
                    nombre = row['id_propietario__username']
                writer.writerow([nombre, row['cantidad'], f"C$ {row['total']}"])
            writer.writerow([])

            writer.writerow(['Citas por día'])
            writer.writerow(['Fecha', 'Cantidad'])
            for row in citas_group:
                writer.writerow([row['period'], row['cantidad']])
            writer.writerow([])

            writer.writerow(['Consultas por día'])
            writer.writerow(['Fecha', 'Cantidad'])
            for row in consultas_group:
                writer.writerow([row['period'], row['cantidad']])
            writer.writerow([])

            writer.writerow(['Mascotas con más consultas'])
            writer.writerow(['Mascota', 'Dueño', 'Consultas'])
            for row in mascotas_frecuentes:
                dueño = f"{row['mascota__owner__first_name']} {row['mascota__owner__last_name']}".strip()
                if not dueño:
                    dueño = row['mascota__owner__username']
                writer.writerow([row['mascota__nombre'], dueño, row['cantidad']])
            writer.writerow([])

            writer.writerow(['Stock crítico'])
            writer.writerow(['Producto', 'Stock', 'Mínimo'])
            for row in stock_critico:
                writer.writerow([row.nombre, row.stock_inicial, row.stock_minimo])

            return resp

        if export == 'pdf':
            return render(request, 'clinica/reportes_print.html', context)

        return render(request, 'clinica/reportes.html', context)


class ExpedienteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Mascota
    template_name = 'clinica/expediente_detail.html'
    context_object_name = 'mascota'
    permission_required = 'clinica.view_mascota'

    def get_queryset(self):
        qs = Mascota.objects.select_related('owner').all()
        user = self.request.user
        is_owner_only = user.groups.filter(name='DUENO').exists() and not user.groups.filter(name__in=['VETERINARIO', 'ASISTENTE', 'INVENTARIO', 'ADMIN']).exists() and not user.is_staff
        if is_owner_only:
            qs = qs.filter(owner=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mascota = self.object
        expediente = getattr(mascota, 'expediente', None)
        consultas = mascota.consultas.select_related('medico').all()

        edad = None
        if mascota.fecha_nacimiento:
            today = timezone.localdate()
            born = mascota.fecha_nacimiento
            edad_years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            edad = f"{edad_years} años"

        ctx.update({
            'expediente': expediente,
            'consultas': consultas,
            'edad': edad,
            'reserva_form': ReservaLoteForm(),
            'reservas_lote': expediente.reservas_lote.select_related('lote__producto', 'created_by').all() if expediente else [],
        })
        return ctx


class ReservaLoteCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'clinica.add_consulta'

    def post(self, request, pk):
        expediente = get_object_or_404(Expediente, pk=pk)
        form = ReservaLoteForm(request.POST)
        if form.is_valid():
            lote = form.cleaned_data['lote']
            qty = form.cleaned_data['cantidad']
            if qty > lote.cantidad:
                messages.error(request, 'La cantidad a reservar excede el stock del lote.')
            else:
                aplicar_reserva_lote(lote, qty, expediente, None, request.user)
                messages.success(request, 'Lote reservado.')
        else:
            messages.error(request, 'No se pudo reservar el lote.')
        return redirect('clinica:expediente_detail', pk=expediente.mascota.pk)


class ReservaLoteCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'clinica.change_consulta'

    def post(self, request, pk):
        reserva = get_object_or_404(ReservaLote, pk=pk)
        if reserva.estado != ReservaLote.ESTADO_RESERVADO:
            return redirect('clinica:expediente_detail', pk=reserva.expediente.mascota.pk)
        lote = reserva.lote
        before = lote.producto.stock_inicial
        lote.cantidad += reserva.cantidad
        lote.save(update_fields=['cantidad'])
        lote.producto.stock_inicial = sum(l.cantidad for l in lote.producto.lotes.all())
        lote.producto.save(update_fields=['stock_inicial'])
        InventoryMovement.objects.create(
            producto=lote.producto,
            tipo=InventoryMovement.TIPO_LIBERACION,
            cantidad=reserva.cantidad,
            stock_before=before,
            stock_after=lote.producto.stock_inicial,
            lote=lote.lote,
            fecha_vencimiento=lote.fecha_vencimiento,
            referencia=f"Liberación reserva #{reserva.id}",
            created_by=request.user if request.user.is_authenticated else None,
        )
        reserva.estado = ReservaLote.ESTADO_CANCELADO
        reserva.save(update_fields=['estado'])
        messages.info(request, 'Reserva cancelada y stock liberado.')
        return redirect('clinica:expediente_detail', pk=reserva.expediente.mascota.pk)


class ReservaLoteUseView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'clinica.change_consulta'

    def post(self, request, pk):
        with transaction.atomic():
            reserva = ReservaLote.objects.select_for_update().filter(pk=pk).first()
            if not reserva:
                return redirect('clinica:dashboard')
            if reserva.estado != ReservaLote.ESTADO_RESERVADO:
                return redirect('clinica:expediente_detail', pk=reserva.expediente.mascota.pk)
            if reserva.venta_id:
                return redirect('inventario:venta_receipt', pk=reserva.venta_id)
            venta = Venta.objects.create(
                id_propietario=getattr(reserva.expediente.mascota, 'owner', None),
                vendedor=getattr(getattr(request.user, 'staff_profile', None), 'pk', None) and request.user.staff_profile or getattr(reserva.consulta, 'medico', None),
                metodo_pago=Venta.METODO_EFECTIVO,
                estado=Venta.ESTADO_PAGADA,
                notas=f"Venta por reserva de lote ({reserva.lote.lote})",
                created_by=request.user if request.user.is_authenticated else None,
                updated_by=request.user if request.user.is_authenticated else None,
                stock_committed=True,
            )
            SaleItem.objects.create(
                venta=venta,
                producto=reserva.lote.producto,
                cantidad=reserva.cantidad,
                precio_unitario=reserva.lote.producto.precio,
                descuento=0,
                lote=reserva.lote.lote,
            )
            from inventario.models import recalc_venta_total
            recalc_venta_total(venta)
            VentaAudit.objects.create(
                venta=venta,
                user=request.user if request.user.is_authenticated else None,
                action='created',
                notes='Venta creada desde reserva de lote'
            )
            reserva.estado = ReservaLote.ESTADO_USADO
            reserva.venta = venta
            reserva.save(update_fields=['estado', 'venta'])
            InventoryMovement.objects.filter(
                tipo=InventoryMovement.TIPO_RESERVA,
                referencia=f"Reserva #{reserva.id}"
            ).update(referencia=f"Reserva #{reserva.id} | Ticket #{venta.id}")
        return redirect('inventario:venta_receipt', pk=venta.pk)


class ConsultaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Consulta
    form_class = ConsultaForm
    template_name = 'clinica/consulta_form.html'
    permission_required = 'clinica.add_consulta'

    def dispatch(self, request, *args, **kwargs):
        self.cita = get_object_or_404(Cita, pk=kwargs.get('pk'))
        # Only assigned veterinarian (or admin) can open the consulta
        if not (has_role(request.user, ROLE_ADMIN) or request.user.is_superuser):
            staff = Staff.objects.filter(user=request.user, is_active=True).first()
            if not staff or self.cita.veterinario_id != staff.id:
                return redirect('clinica:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mascota'] = self.cita.mascota
        ctx['cita'] = self.cita
        if self.request.POST:
            ctx['receta_formset'] = RecetaItemFormSet(self.request.POST, prefix='receta')
        else:
            ctx['receta_formset'] = RecetaItemFormSet(prefix='receta')
        return ctx

    def form_valid(self, form):
        receta_formset = RecetaItemFormSet(self.request.POST, prefix='receta')
        if not receta_formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.mascota = self.cita.mascota
            obj.cita = self.cita
            obj.medico = self.cita.veterinario
            cerrar = form.cleaned_data.get('cerrar_consulta')
            if cerrar:
                obj.estado = Consulta.ESTADO_CERRADA
                obj.cerrada_en = timezone.now()
            obj.save()
            if receta_formset.has_changed():
                receta = Receta.objects.create(
                    consulta=obj,
                    mascota=self.cita.mascota,
                    created_by=self.request.user if self.request.user.is_authenticated else None,
                )
                receta_formset.instance = receta
                receta_formset.save()
        # Update cita status if consulta closed
        if cerrar:
            self.cita.estado = Cita.ESTADO_ATENDIDA
            self.cita.save(update_fields=['estado'])
            log_cita_event(self.cita, CitaEvent.TIPO_ATENDIDA, self.request.user)
        # Create follow-up cita if requested
        seguimiento_fecha = form.cleaned_data.get('seguimiento_fecha')
        if seguimiento_fecha:
            seguimiento_slot = seguimiento_fecha
            if self.cita.veterinario:
                steps = 0
                while Cita.objects.filter(veterinario=self.cita.veterinario, fecha=seguimiento_slot).exists():
                    seguimiento_slot = seguimiento_slot + timedelta(minutes=30)
                    steps += 1
                    if steps > 48:
                        break
            if seguimiento_slot != seguimiento_fecha:
                messages.info(self.request, 'Horario ocupado. La cita de seguimiento se movió al espacio más cercano disponible.')
            cita = Cita.objects.create(
                mascota=self.cita.mascota,
                fecha=seguimiento_slot,
                veterinario=self.cita.veterinario,
                estado=Cita.ESTADO_PENDIENTE,
                created_by=self.request.user,
                notas='Cita de seguimiento'
            )
            log_cita_event(cita, CitaEvent.TIPO_CREADA, self.request.user, 'Cita de seguimiento')
            log_cita_event(cita, CitaEvent.TIPO_ORIGEN_DIRECTA, self.request.user)
            create_cita_reminders(cita, self.request.user)
        elif cerrar and getattr(settings, 'FOLLOWUP_AUTO_ENABLED', False):
            days = getattr(settings, 'FOLLOWUP_AUTO_DAYS', 30)
            followup_date = timezone.now() + timedelta(days=days)
            cita = Cita.objects.create(
                mascota=self.cita.mascota,
                fecha=followup_date,
                veterinario=self.cita.veterinario,
                estado=Cita.ESTADO_PENDIENTE,
                created_by=self.request.user,
                notas=f'Cita de seguimiento automático ({days} días)'
            )
            log_cita_event(cita, CitaEvent.TIPO_CREADA, self.request.user, f'Seguimiento automático ({days} días)')
            log_cita_event(cita, CitaEvent.TIPO_ORIGEN_DIRECTA, self.request.user)
            create_cita_reminders(cita, self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clinica:expediente_detail', args=[self.cita.mascota.pk])


class RecetaApproveView(LoginRequiredMixin, View):

    def post(self, request, pk):
        receta = get_object_or_404(Receta, pk=pk)
        can_manage = (
            has_role(request.user, ROLE_ADMIN) or
            has_role(request.user, ROLE_ASISTENTE) or
            request.user.is_superuser
        )
        if not can_manage:
            return redirect('clinica:dashboard')
        if receta.estado != Receta.ESTADO_PENDIENTE:
            return redirect('clinica:cita_detail', pk=receta.consulta.cita_id)
        if not receta.items.exists():
            messages.error(request, 'La receta no tiene ítems para generar la venta.')
            return redirect('clinica:cita_detail', pk=receta.consulta.cita_id)
        with transaction.atomic():
            venta = create_venta_from_receta(receta, request.user, mark_paid=True)
            receta.estado = Receta.ESTADO_ACEPTADA
            receta.venta = venta
            receta.save(update_fields=['estado', 'venta', 'updated_at'])
        messages.success(request, 'Receta aceptada. Se creó la venta y se descontó stock.')
        back = request.META.get('HTTP_REFERER')
        if back:
            return redirect(back)
        return redirect('clinica:cita_detail', pk=receta.consulta.cita_id)


class RecetaRejectView(LoginRequiredMixin, View):

    def post(self, request, pk):
        receta = get_object_or_404(Receta, pk=pk)
        can_manage = (
            has_role(request.user, ROLE_ADMIN) or
            has_role(request.user, ROLE_ASISTENTE) or
            request.user.is_superuser
        )
        if not can_manage:
            return redirect('clinica:dashboard')
        if receta.estado != Receta.ESTADO_PENDIENTE:
            return redirect('clinica:cita_detail', pk=receta.consulta.cita_id)
        receta.estado = Receta.ESTADO_RECHAZADA
        receta.save(update_fields=['estado', 'updated_at'])
        messages.info(request, 'Receta rechazada.')
        back = request.META.get('HTTP_REFERER')
        if back:
            return redirect(back)
        return redirect('clinica:cita_detail', pk=receta.consulta.cita_id)


class RecetaPrintView(LoginRequiredMixin, DetailView):
    model = Receta
    template_name = 'clinica/receta_print.html'
    context_object_name = 'receta'

    def get_queryset(self):
        qs = Receta.objects.select_related('mascota', 'consulta', 'consulta__cita', 'consulta__medico', 'venta')
        if has_role(self.request.user, ROLE_VETERINARIO):
            staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
            if staff:
                qs = qs.filter(consulta__cita__veterinario=staff)
        elif is_owner_only(self.request.user):
            qs = qs.filter(mascota__owner=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        receta = self.object
        config = get_venta_config()
        rate = Decimal(str(config.iva_rate or 0))
        receta_items_priced = []
        receta_total = Decimal('0')
        for item in receta.items.select_related('producto').all():
            price_base = Decimal(str(item.producto.precio or 0))
            price_final = (price_base * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            line_total = (price_final * Decimal(item.cantidad)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            receta_total += line_total
            receta_items_priced.append({
                'item': item,
                'price_final': price_final,
                'line_total': line_total,
            })
        ctx['receta_items_priced'] = receta_items_priced
        ctx['receta_total'] = receta_total
        return ctx


class CitaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Cita
    form_class = CitaForm
    template_name = 'clinica/cita_form.html'
    permission_required = 'clinica.add_cita'

    def dispatch(self, request, *args, **kwargs):
        if not (has_role(request.user, ROLE_ADMIN) or has_role(request.user, ROLE_ASISTENTE) or request.user.is_superuser):
            return redirect('clinica:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.origen = Cita.ORIGEN_DIRECTA
        # Si hay conflicto, buscar el espacio más cercano (30 min, hasta 24h)
        if obj.veterinario and obj.fecha:
            slot = obj.fecha
            steps = 0
            while Cita.objects.filter(veterinario=obj.veterinario, fecha=slot).exists():
                slot = slot + timedelta(minutes=30)
                steps += 1
                if steps > 48:
                    break
            if slot != obj.fecha:
                obj.fecha = slot
                messages.info(self.request, 'Horario ocupado. Se asignó la cita al espacio más cercano disponible.')
        obj.save()
        log_cita_event(obj, CitaEvent.TIPO_CREADA, self.request.user)
        log_cita_event(obj, CitaEvent.TIPO_ORIGEN_DIRECTA, self.request.user)
        create_cita_reminders(obj, self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clinica:cita_list')

    def get_initial(self):
        initial = super().get_initial()
        mascota_id = self.request.GET.get('mascota')
        if mascota_id:
            initial['mascota'] = mascota_id
        return initial


class CitaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Cita
    template_name = 'clinica/cita_list.html'
    context_object_name = 'citas'
    permission_required = 'clinica.view_cita'

    def get_queryset(self):
        ultima_consulta_fecha = Consulta.objects.filter(cita_id=OuterRef('pk')).order_by('-fecha').values('fecha')[:1]
        qs = Cita.objects.select_related('mascota', 'veterinario').annotate(
            ultima_consulta_fecha=Subquery(ultima_consulta_fecha)
        )
        if has_role(self.request.user, ROLE_VETERINARIO):
            staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
            if staff:
                qs = qs.filter(veterinario=staff)
        elif has_role(self.request.user, ROLE_ASISTENTE) or has_role(self.request.user, ROLE_ADMIN) or self.request.user.is_superuser:
            qs = qs
        elif is_owner_only(self.request.user):
            qs = qs.filter(mascota__owner=self.request.user)
        return qs.order_by('fecha')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        citas_qs = ctx['citas']
        citas_ids = list(citas_qs.values_list('id', flat=True))
        receta_pendiente_ids = set()
        if citas_ids:
            receta_pendiente_ids = set(
                Receta.objects.filter(
                    consulta__cita_id__in=citas_ids,
                    estado=Receta.ESTADO_PENDIENTE
                ).values_list('consulta__cita_id', flat=True)
            )
        ctx['receta_pendiente_ids'] = receta_pendiente_ids
        ctx['citas_por_confirmar'] = citas_qs.filter(estado=Cita.ESTADO_PENDIENTE).order_by('fecha')
        ctx['citas_confirmadas'] = citas_qs.filter(
            estado__in=[Cita.ESTADO_CONFIRMADA, Cita.ESTADO_REPROGRAMADA]
        ).order_by('fecha')
        ctx['citas_canceladas'] = citas_qs.filter(estado=Cita.ESTADO_CANCELADA).order_by('-fecha')
        ctx['citas_atendidas'] = citas_qs.filter(estado=Cita.ESTADO_ATENDIDA).order_by('-ultima_consulta_fecha', '-fecha')
        return ctx


class CitaHistoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CitaEvent
    template_name = 'clinica/cita_history_list.html'
    context_object_name = 'events'
    paginate_by = 50
    permission_required = 'clinica.view_cita'

    def get_queryset(self):
        qs = CitaEvent.objects.select_related('cita', 'cita__mascota', 'created_by').all()
        cita_id = self.request.GET.get('cita')
        if cita_id:
            qs = qs.filter(cita_id=cita_id)
        if has_role(self.request.user, ROLE_VETERINARIO):
            staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
            if staff:
                qs = qs.filter(cita__veterinario=staff)
        elif is_owner_only(self.request.user):
            return CitaEvent.objects.none()
        return qs


class CitaCalendarView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'clinica/cita_calendar.html'
    permission_required = 'clinica.view_cita'


class CitaEventsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'clinica.view_cita'

    def get(self, request):
        qs = Cita.objects.select_related('mascota', 'veterinario').all()
        if has_role(request.user, ROLE_VETERINARIO):
            staff = Staff.objects.filter(user=request.user, is_active=True).first()
            if staff:
                qs = qs.filter(veterinario=staff)
        elif has_role(request.user, ROLE_ASISTENTE) or has_role(request.user, ROLE_ADMIN) or request.user.is_superuser:
            qs = qs
        elif is_owner_only(request.user):
            qs = qs.filter(mascota__owner=request.user)

        start = request.GET.get('start')
        end = request.GET.get('end')
        if start:
            dt = parse_datetime(start)
            if not dt:
                try:
                    dt = timezone.datetime.fromisoformat(start)
                except ValueError:
                    dt = None
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            if dt:
                qs = qs.filter(fecha__gte=dt)
        if end:
            dt = parse_datetime(end)
            if not dt:
                try:
                    dt = timezone.datetime.fromisoformat(end)
                except ValueError:
                    dt = None
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            if dt:
                qs = qs.filter(fecha__lte=dt)

        def color_for_estado(estado):
            if estado == Cita.ESTADO_CANCELADA:
                return '#e11d48'
            if estado == Cita.ESTADO_ATENDIDA:
                return '#10b981'
            if estado == Cita.ESTADO_CONFIRMADA:
                return '#0ea5a4'
            if estado == Cita.ESTADO_REPROGRAMADA:
                return '#f59e0b'
            return '#64748b'

        events = []
        for c in qs:
            title = f"{c.mascota.nombre}"
            if c.veterinario:
                title = f"{title} — {c.veterinario.nombre_completo}"
            events.append({
                'id': c.id,
                'title': title,
                'start': c.fecha.isoformat(),
                'url': reverse('clinica:cita_detail', args=[c.id]),
                'color': color_for_estado(c.estado),
            })

        return JsonResponse(events, safe=False)


class CitaReminderGenerateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'clinica.view_cita'

    def post(self, request):
        if not (has_role(request.user, ROLE_ASISTENTE) or has_role(request.user, ROLE_ADMIN) or request.user.is_superuser):
            return redirect('clinica:dashboard')
        now = timezone.now()
        created = 0
        for cita in Cita.objects.filter(fecha__gte=now).order_by('fecha')[:20]:
            created += create_cita_reminders(cita, request.user)
        messages.success(request, f'Recordatorios generados: {created}')
        return redirect('clinica:dashboard')


class CitaReminderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CitaReminder
    template_name = 'clinica/cita_reminder_list.html'
    context_object_name = 'reminders'
    paginate_by = 50
    permission_required = 'clinica.view_cita'

    def get_queryset(self):
        qs = CitaReminder.objects.select_related('cita', 'cita__mascota').all()
        estado = self.request.GET.get('estado')
        if estado is None or estado == '':
            estado = CitaReminder.ESTADO_PENDIENTE
        canal = self.request.GET.get('canal')
        mascota = self.request.GET.get('mascota')
        if estado:
            qs = qs.filter(estado=estado)
        if canal:
            qs = qs.filter(canal=canal)
        if mascota:
            qs = qs.filter(cita__mascota_id=mascota)
        if has_role(self.request.user, ROLE_VETERINARIO):
            staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
            if staff:
                qs = qs.filter(cita__veterinario=staff)
        elif has_role(self.request.user, ROLE_ASISTENTE) or has_role(self.request.user, ROLE_ADMIN) or self.request.user.is_superuser:
            qs = qs
        elif is_owner_only(self.request.user):
            qs = qs.filter(cita__mascota__owner=self.request.user)
        return qs.order_by('-programado_para')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estado_choices'] = CitaReminder.ESTADO_CHOICES
        ctx['canal_choices'] = CitaReminder.CANAL_CHOICES
        ctx['mascotas'] = Mascota.objects.order_by('nombre')
        return ctx


class CitaReminderSwitchChannelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'clinica.change_citareminder'

    def post(self, request, pk):
        reminder = get_object_or_404(CitaReminder, pk=pk)
        if reminder.estado != CitaReminder.ESTADO_PENDIENTE:
            return redirect('clinica:cita_reminder_list')
        reminder.canal = CitaReminder.CANAL_WHATSAPP
        reminder.save(update_fields=['canal'])
        messages.success(request, 'Canal actualizado a WhatsApp.')
        return redirect('clinica:cita_reminder_list')


class CitaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Cita
    form_class = CitaForm
    template_name = 'clinica/cita_form.html'
    permission_required = 'clinica.change_cita'

    def get_success_url(self):
        return reverse('clinica:cita_detail', args=[self.object.pk])


class CitaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Cita
    template_name = 'clinica/cita_detail.html'
    context_object_name = 'cita'
    permission_required = 'clinica.view_cita'

    def get_queryset(self):
        qs = Cita.objects.select_related('mascota', 'veterinario')
        if has_role(self.request.user, ROLE_VETERINARIO):
            staff = Staff.objects.filter(user=self.request.user, is_active=True).first()
            if staff:
                qs = qs.filter(veterinario=staff)
        elif has_role(self.request.user, ROLE_ASISTENTE) or has_role(self.request.user, ROLE_ADMIN) or self.request.user.is_superuser:
            qs = qs
        elif is_owner_only(self.request.user):
            qs = qs.filter(mascota__owner=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['historial'] = self.object.historial.select_related('created_by').all()
        ultima_consulta = self.object.consultas.select_related('medico').order_by('-fecha').first()
        ctx['ultima_consulta'] = ultima_consulta
        ultima_receta = None
        receta_items_priced = []
        receta_total = Decimal('0')
        if ultima_consulta:
            try:
                ultima_receta = ultima_consulta.receta
            except Receta.DoesNotExist:
                ultima_receta = None
        if ultima_receta:
            config = get_venta_config()
            rate = Decimal(str(config.iva_rate or 0))
            for item in ultima_receta.items.select_related('producto').all():
                price_base = Decimal(str(item.producto.precio or 0))
                price_final = (price_base * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                line_total = (price_final * Decimal(item.cantidad)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                receta_total += line_total
                receta_items_priced.append({
                    'item': item,
                    'price_final': price_final,
                    'line_total': line_total,
                })
        ctx['ultima_receta'] = ultima_receta
        ctx['receta_items_priced'] = receta_items_priced
        ctx['receta_total'] = receta_total
        ctx['is_dueno'] = is_owner_only(self.request.user)
        ctx['is_admin'] = has_role(self.request.user, ROLE_ADMIN) or self.request.user.is_superuser
        ctx['can_receta_manage'] = (
            has_role(self.request.user, ROLE_ADMIN) or
            has_role(self.request.user, ROLE_ASISTENTE) or
            self.request.user.is_superuser
        )
        return ctx


class CitaStatusUpdateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        cita = get_object_or_404(Cita, pk=pk)
        action = request.POST.get('action')
        is_owner = is_owner_only(request.user) and cita.mascota.owner_id == request.user.id
        can_manage = (
            request.user.has_perm('clinica.change_cita') or
            has_role(request.user, ROLE_ADMIN) or
            has_role(request.user, ROLE_ASISTENTE) or
            request.user.is_superuser
        )
        if action == 'confirmar':
            if cita.estado != Cita.ESTADO_PENDIENTE:
                return redirect('clinica:cita_detail', pk=cita.pk)
            if not (can_manage or is_owner):
                return redirect('clinica:cita_detail', pk=cita.pk)
            cita.estado = Cita.ESTADO_CONFIRMADA
        elif action == 'cancelar':
            if not (can_manage or is_owner):
                return redirect('clinica:cita_detail', pk=cita.pk)
            if cita.estado in [Cita.ESTADO_ATENDIDA, Cita.ESTADO_CANCELADA]:
                return redirect('clinica:cita_detail', pk=cita.pk)
            cita.estado = Cita.ESTADO_CANCELADA
        else:
            return redirect('clinica:cita_detail', pk=cita.pk)
        cita.save(update_fields=['estado'])
        if action == 'confirmar':
            log_cita_event(cita, CitaEvent.TIPO_CONFIRMADA, request.user)
        elif action == 'cancelar':
            log_cita_event(cita, CitaEvent.TIPO_CANCELADA, request.user)
        back = request.META.get('HTTP_REFERER')
        if back:
            return redirect(back)
        return redirect('clinica:cita_detail', pk=cita.pk)


class SolicitudCitaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SolicitudCita
    form_class = SolicitudCitaForm
    template_name = 'clinica/solicitud_cita_form.html'
    permission_required = 'clinica.add_solicitudcita'

    def get_initial(self):
        initial = super().get_initial()
        mascota_id = self.request.GET.get('mascota')
        if mascota_id:
            initial['mascota'] = mascota_id
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Owners should only see their own mascotas
        if is_owner_only(self.request.user):
            form.fields['mascota'].queryset = Mascota.objects.filter(owner=self.request.user).order_by('nombre')
        return form

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.solicitado_por = self.request.user
        obj.save()
        messages.success(self.request, 'Solicitud enviada. Te notificaremos cuando sea atendida.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clinica:dashboard')


class SolicitudCitaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = SolicitudCita
    template_name = 'clinica/solicitud_cita_list.html'
    context_object_name = 'solicitudes'
    permission_required = 'clinica.view_solicitudcita'

    def get_queryset(self):
        qs = SolicitudCita.objects.select_related('mascota', 'solicitado_por').all()
        if is_owner_only(self.request.user):
            qs = qs.filter(solicitado_por=self.request.user)
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['veterinarios'] = Staff.objects.filter(is_active=True, cargo__in=['VETERINARIO', 'ADMIN']).order_by('nombre_completo')
        ctx['cita_asignada_msg'] = self.request.session.pop('cita_asignada_msg', None)
        return ctx


class SolicitudCitaApproveView(LoginRequiredMixin, View):

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudCita, pk=pk)
        if solicitud.estado != SolicitudCita.ESTADO_PENDIENTE:
            return redirect('clinica:solicitud_cita_list')
        can_manage = (
            request.user.has_perm('clinica.change_solicitudcita') or
            has_role(request.user, ROLE_ADMIN) or
            has_role(request.user, ROLE_ASISTENTE) or
            request.user.is_superuser
        )
        if not can_manage:
            return redirect('clinica:solicitud_cita_list')
        action = request.POST.get('action', 'aprobar')
        if action == 'rechazar':
            solicitud.estado = SolicitudCita.ESTADO_RECHAZADA
            solicitud.save(update_fields=['estado', 'updated_at'])
            messages.info(request, 'Solicitud rechazada.')
            return redirect('clinica:solicitud_cita_list')

        veterinario_id = request.POST.get('veterinario')
        fecha = request.POST.get('fecha')
        # Create cita
        if not veterinario_id:
            messages.error(request, 'Selecciona veterinario para asignar.')
            return redirect('clinica:solicitud_cita_list')
        if not fecha:
            if solicitud.fecha_preferida:
                fecha = solicitud.fecha_preferida.isoformat()
            else:
                messages.error(request, 'Selecciona fecha para asignar o agrega una fecha preferida.')
                return redirect('clinica:solicitud_cita_list')

        veterinario = get_object_or_404(Staff, pk=veterinario_id)
        # Parse datetime
        dt = parse_datetime(fecha)
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        if not dt:
            messages.error(request, 'Fecha inválida.')
            return redirect('clinica:solicitud_cita_list')

        # Find nearest available slot if conflict
        slot = dt
        steps = 0
        while Cita.objects.filter(veterinario=veterinario, fecha=slot).exists():
            slot = slot + timedelta(minutes=30)
            steps += 1
            if steps > 48:  # 24 hours range
                break
        cita = Cita.objects.create(
            mascota=solicitud.mascota,
            fecha=slot,
            veterinario=veterinario,
            estado=Cita.ESTADO_CONFIRMADA,
            origen=Cita.ORIGEN_SOLICITUD,
            created_by=request.user,
            notas=solicitud.motivo
        )
        log_cita_event(cita, CitaEvent.TIPO_CREADA, request.user, 'Creada desde solicitud')
        log_cita_event(cita, CitaEvent.TIPO_ORIGEN_SOLICITUD, request.user)
        log_cita_event(cita, CitaEvent.TIPO_CONFIRMADA, request.user)
        create_cita_reminders(cita, request.user)
        solicitud.estado = SolicitudCita.ESTADO_ATENDIDA
        solicitud.cita_asignada = cita
        solicitud.save(update_fields=['estado', 'updated_at', 'cita_asignada'])
        if slot != dt:
            request.session['cita_asignada_msg'] = 'El horario solicitado estaba ocupado. Se asignó la cita al horario disponible más cercano.'
        return redirect('clinica:solicitud_cita_list')


class SolicitudReprogramacionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SolicitudReprogramacion
    form_class = SolicitudReprogramacionForm
    template_name = 'clinica/solicitud_reprogramacion_form.html'
    permission_required = 'clinica.add_solicitudreprogramacion'

    def dispatch(self, request, *args, **kwargs):
        self.cita = get_object_or_404(Cita, pk=kwargs.get('pk'))
        is_owner = self.cita.mascota.owner_id == request.user.id
        if is_owner:
            return super().dispatch(request, *args, **kwargs)
        # Only assigned veterinarian can request reprogramation
        staff = Staff.objects.filter(user=request.user, is_active=True).first()
        if not staff or self.cita.veterinario_id != staff.id:
            return redirect('clinica:cita_detail', pk=self.cita.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.cita = self.cita
        obj.solicitado_por = self.request.user
        if obj.nueva_fecha and self.cita.veterinario:
            slot = obj.nueva_fecha
            steps = 0
            while Cita.objects.filter(veterinario=self.cita.veterinario, fecha=slot).exclude(pk=self.cita.pk).exists():
                slot = slot + timedelta(minutes=30)
                steps += 1
                if steps > 48:
                    break
            if slot != obj.nueva_fecha:
                obj.nueva_fecha = slot
                messages.info(self.request, 'Horario ocupado. Se propuso el espacio más cercano disponible para la reprogramación.')
        obj.save()
        log_cita_event(self.cita, CitaEvent.TIPO_REPROG_SOLICITADA, self.request.user, obj.descripcion)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clinica:cita_detail', args=[self.cita.pk])


class SolicitudReprogramacionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = SolicitudReprogramacion
    template_name = 'clinica/solicitud_reprogramacion_list.html'
    context_object_name = 'solicitudes'
    permission_required = 'clinica.view_solicitudreprogramacion'

    def get_queryset(self):
        qs = SolicitudReprogramacion.objects.select_related('cita__mascota', 'cita__veterinario', 'solicitado_por')
        if has_role(self.request.user, ROLE_VETERINARIO):
            qs = qs.filter(solicitado_por=self.request.user)
        elif has_role(self.request.user, ROLE_ASISTENTE) or has_role(self.request.user, ROLE_ADMIN) or self.request.user.is_superuser:
            qs = qs
        elif is_owner_only(self.request.user):
            qs = qs.filter(solicitado_por=self.request.user)
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reprog_error'] = self.request.session.pop('reprog_error', None)
        ctx['is_veterinario'] = has_role(self.request.user, ROLE_VETERINARIO)
        return ctx


class SolicitudReprogramacionApproveView(LoginRequiredMixin, View):

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudReprogramacion, pk=pk)
        if solicitud.estado != SolicitudReprogramacion.ESTADO_PENDIENTE:
            return redirect('clinica:solicitud_reprogramacion_list')
        can_manage = (
            request.user.has_perm('clinica.change_solicitudreprogramacion') or
            has_role(request.user, ROLE_ADMIN) or
            has_role(request.user, ROLE_ASISTENTE) or
            request.user.is_superuser
        )
        if not can_manage:
            return redirect('clinica:solicitud_reprogramacion_list')

        cita = solicitud.cita
        veterinario = cita.veterinario
        nueva_fecha = solicitud.nueva_fecha
        # Validate conflicts for same veterinarian
        conflict = Cita.objects.filter(
            veterinario=veterinario,
            fecha=nueva_fecha
        ).exclude(pk=cita.pk).exists()
        if conflict:
            solicitud.estado = SolicitudReprogramacion.ESTADO_RECHAZADA
            solicitud.motivo_rechazo = 'No se pudo aprobar: el veterinario ya tiene una cita en esa fecha y hora.'
            solicitud.save(update_fields=['estado', 'motivo_rechazo'])
            log_cita_event(cita, CitaEvent.TIPO_REPROG_RECHAZADA, request.user, solicitud.motivo_rechazo)
            request.session['reprog_error'] = solicitud.motivo_rechazo
            return redirect('clinica:solicitud_reprogramacion_list')

        cita.fecha = nueva_fecha
        cita.estado = Cita.ESTADO_REPROGRAMADA
        cita.save(update_fields=['fecha', 'estado'])
        solicitud.estado = SolicitudReprogramacion.ESTADO_APROBADA
        solicitud.save(update_fields=['estado'])
        log_cita_event(cita, CitaEvent.TIPO_REPROG_APROBADA, request.user, f"Nueva fecha: {nueva_fecha}")
        return redirect('clinica:solicitud_reprogramacion_list')


class SolicitudReprogramacionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SolicitudReprogramacion
    form_class = SolicitudReprogramacionForm
    template_name = 'clinica/solicitud_reprogramacion_form.html'
    permission_required = 'clinica.change_solicitudreprogramacion'

    def get_queryset(self):
        return SolicitudReprogramacion.objects.select_related('cita', 'solicitado_por')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        # Only requester can edit their own request
        if obj.solicitado_por_id != request.user.id:
            return redirect('clinica:cita_detail', pk=obj.cita_id)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.estado = SolicitudReprogramacion.ESTADO_PENDIENTE
        obj.motivo_rechazo = ''
        obj.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clinica:cita_detail', args=[self.object.cita_id])


class MascotaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Mascota
    form_class = MascotaForm
    template_name = 'clinica/mascota_form.html'
    permission_required = 'clinica.change_mascota'

    def get_success_url(self):
        return reverse('clinica:expediente_detail', args=[self.object.pk])


class MascotaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Mascota
    form_class = MascotaForm
    template_name = 'clinica/mascota_form.html'
    permission_required = 'clinica.add_mascota'

    def form_valid(self, form):
        if not form.instance.owner and is_owner_only(self.request.user):
            form.instance.owner = self.request.user
        response = super().form_valid(form)
        Expediente.objects.get_or_create(mascota=self.object)
        return response

    def get_success_url(self):
        return reverse('clinica:expediente_detail', args=[self.object.pk])


@method_decorator(vary_on_cookie, name='dispatch')
@method_decorator(cache_page(60), name='dispatch')
class MascotaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Mascota
    template_name = 'clinica/mascota_list.html'
    context_object_name = 'mascotas'
    permission_required = 'clinica.view_mascota'

    def get_queryset(self):
        qs = Mascota.objects.select_related('owner').all()
        q = self.request.GET.get('q')
        user = self.request.user
        if is_owner_only(user):
            qs = qs.filter(owner=user)
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) |
                Q(especie__icontains=q) |
                Q(raza__icontains=q) |
                Q(owner__username__icontains=q) |
                Q(owner__first_name__icontains=q) |
                Q(owner__last_name__icontains=q)
            )
        return qs

