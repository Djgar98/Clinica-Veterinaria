from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, F, Sum, Count, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views import View
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django import forms
import json
import csv

from .models import Producto, Venta, VentaAudit, Recordatorio, SaleItem, SolicitudAnulacionVenta, InventoryMovement, StockAdjustmentRequest, ProductoLote, get_venta_config, TipoDescuento
from usuarios.roles import is_owner_only


def _get_tipo_descuentos_map():
    return {d.tipo: d for d in TipoDescuento.objects.all()}


def _get_descuento_pct_for_producto(prod, today, tipo_desc_map):
    if prod.descuento_activo(today):
        return Decimal(str(prod.descuento_pct or 0))
    tipo_desc = tipo_desc_map.get(prod.tipo)
    if tipo_desc and tipo_desc.descuento_activo(today):
        return Decimal(str(tipo_desc.descuento_pct or 0))
    return None


def build_products_map():
    products = Producto.objects.filter(is_active=True).prefetch_related('lotes')
    config = get_venta_config()
    rate = Decimal(str(config.iva_rate or 0))
    today = timezone.localdate()
    tipo_desc_map = _get_tipo_descuentos_map()
    data = {}
    for p in products:
        price_base = Decimal(str(p.precio or 0))
        price_final = (price_base * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        descuento_pct = _get_descuento_pct_for_producto(p, today, tipo_desc_map)
        lotes = []
        if p.tipo == Producto.TIPO_MEDICAMENTO:
            for l in p.lotes.all().order_by('fecha_vencimiento', 'created_at'):
                if l.cantidad <= 0:
                    continue
                lotes.append({
                    'lote': l.lote,
                    'vencimiento': l.fecha_vencimiento.isoformat() if l.fecha_vencimiento else '',
                    'stock': l.cantidad,
                })
        data[str(p.id)] = {
            'price': str(price_final),
            'price_base': str(price_base),
            'stock': p.stock_inicial,
            'stock_minimo': p.stock_minimo,
            'codigo': p.codigo or '',
            'name': p.nombre,
            'tipo': p.tipo,
            'discount_pct': str(descuento_pct or 0),
            'discount_active': bool(descuento_pct and descuento_pct > 0),
            'lote': p.lote or '',
            'vencimiento': p.fecha_vencimiento.isoformat() if p.fecha_vencimiento else '',
            'lotes': lotes,
        }
    return data
from .forms import ProductoForm, VentaForm, VentaItemFormSet, RecordatorioForm, StockAdjustmentRequestForm, VentaConfigForm, ProductoDescuentoCreateForm


class ProductoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'inventario/producto_form.html'
    success_url = reverse_lazy('inventario:list')
    permission_required = 'inventario.add_producto'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        producto = self.object
        if producto.tipo != Producto.TIPO_SERVICIO and producto.stock_inicial > 0:
            if producto.tipo == Producto.TIPO_MEDICAMENTO and (producto.lote or producto.fecha_vencimiento):
                lote, _ = ProductoLote.objects.get_or_create(
                    producto=producto,
                    lote=producto.lote or 'SIN-LOTE',
                    fecha_vencimiento=producto.fecha_vencimiento,
                    defaults={'cantidad': 0},
                )
                lote.cantidad += producto.stock_inicial
                lote.save(update_fields=['cantidad'])
            InventoryMovement.objects.create(
                producto=producto,
                tipo=InventoryMovement.TIPO_ENTRADA,
                cantidad=producto.stock_inicial,
                stock_before=0,
                stock_after=producto.stock_inicial,
                lote=producto.lote or '',
                fecha_vencimiento=producto.fecha_vencimiento,
                referencia='Stock inicial',
                created_by=self.request.user if self.request.user.is_authenticated else None,
            )
        return response




class ProductoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = 'inventario/producto_detail.html'
    context_object_name = 'producto'
    permission_required = 'inventario.view_producto'

    def get_queryset(self):
        return Producto.objects.select_related('categoria').prefetch_related('lotes')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        producto = ctx.get('producto')
        if producto:
            ctx['movimientos'] = InventoryMovement.objects.filter(producto=producto).select_related('created_by')[:10]
            ctx['ventas_items'] = SaleItem.objects.filter(producto=producto).select_related('venta')[:10]
            config = get_venta_config()
            rate = Decimal(str(config.iva_rate or 0))
            producto.precio_con_iva = (Decimal(str(producto.precio or 0)) * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            today = timezone.localdate()
            tipo_desc = _get_tipo_descuentos_map().get(producto.tipo)
            producto.descuento_tipo_pct = tipo_desc.descuento_pct if tipo_desc and tipo_desc.descuento_activo(today) else None
        return ctx

class ProductoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'inventario/producto_form.html'
    success_url = reverse_lazy('inventario:list')
    permission_required = 'inventario.change_producto'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ProductoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Producto
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'
    permission_required = 'inventario.view_producto'

    def get_queryset(self):
        qs = Producto.objects.select_related('categoria').prefetch_related('lotes').all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        productos = list(ctx.get('productos') or [])
        today = timezone.localdate()
        limit = today + timedelta(days=30)
        config = get_venta_config()
        rate = Decimal(str(config.iva_rate or 0))
        tipo_desc_map = _get_tipo_descuentos_map()
        for p in productos:
            p.precio_con_iva = (Decimal(str(p.precio or 0)) * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            tipo_desc = tipo_desc_map.get(p.tipo)
            p.descuento_tipo_pct = tipo_desc.descuento_pct if tipo_desc and tipo_desc.descuento_activo(today) else None
            if p.tipo == Producto.TIPO_MEDICAMENTO:
                expiring = []
                expired = []
                for l in p.lotes.all():
                    if l.cantidad <= 0 or not l.fecha_vencimiento:
                        continue
                    if l.fecha_vencimiento < today:
                        expired.append(l)
                    elif l.fecha_vencimiento <= limit:
                        expiring.append(l)
                p.expiring_lotes = expiring
                p.expired_lotes = expired
            else:
                p.expiring_lotes = []
                p.expired_lotes = []
        ctx['productos'] = productos
        return ctx


class ProductoToggleActiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_producto'

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto.is_active = not producto.is_active
        producto.save(update_fields=['is_active'])
        return redirect('inventario:list')


class ProductoDescuentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Producto
    template_name = 'inventario/producto_descuento_list.html'
    context_object_name = 'productos'
    permission_required = 'inventario.change_producto'

    def get_queryset(self):
        qs = Producto.objects.filter(descuento_pct__gt=0).order_by('nombre')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tipo_descuentos'] = TipoDescuento.objects.filter(descuento_pct__gt=0).order_by('tipo')
        return ctx


class ProductoDescuentoCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'inventario/producto_descuento_form.html'
    permission_required = 'inventario.change_producto'

    def get(self, request):
        form = ProductoDescuentoCreateForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProductoDescuentoCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Descuento creado.')
            return redirect('inventario:producto_descuentos')
        return render(request, self.template_name, {'form': form})


class ProductoDescuentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'inventario/producto_descuento_form.html'
    permission_required = 'inventario.change_producto'

    def get(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        form = ProductoDescuentoCreateForm(initial={
            'aplica_a': ProductoDescuentoCreateForm.APLICA_PRODUCTO,
            'producto': producto.pk,
            'descuento_pct': producto.descuento_pct,
            'descuento_desde': producto.descuento_desde.isoformat() if producto.descuento_desde else '',
            'descuento_hasta': producto.descuento_hasta.isoformat() if producto.descuento_hasta else '',
        })
        form.fields['aplica_a'].widget = forms.HiddenInput()
        form.fields['producto'].widget = forms.HiddenInput()
        form.fields['tipo'].widget = forms.HiddenInput()
        return render(request, self.template_name, {'form': form, 'producto': producto})

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        form = ProductoDescuentoCreateForm(request.POST, initial={'aplica_a': ProductoDescuentoCreateForm.APLICA_PRODUCTO, 'producto': producto.pk})
        form.fields['aplica_a'].widget = forms.HiddenInput()
        form.fields['producto'].widget = forms.HiddenInput()
        form.fields['tipo'].widget = forms.HiddenInput()
        if form.is_valid():
            form.save()
            messages.success(request, 'Descuento actualizado.')
            return redirect('inventario:producto_descuentos')
        return render(request, self.template_name, {'form': form, 'producto': producto})


class TipoDescuentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'inventario/producto_descuento_form.html'
    permission_required = 'inventario.change_producto'

    def get(self, request, tipo):
        descuento = get_object_or_404(TipoDescuento, tipo=tipo)
        form = ProductoDescuentoCreateForm(initial={
            'aplica_a': ProductoDescuentoCreateForm.APLICA_TIPO,
            'tipo': descuento.tipo,
            'descuento_pct': descuento.descuento_pct,
            'descuento_desde': descuento.descuento_desde.isoformat() if descuento.descuento_desde else '',
            'descuento_hasta': descuento.descuento_hasta.isoformat() if descuento.descuento_hasta else '',
        })
        form.fields['aplica_a'].widget = forms.HiddenInput()
        form.fields['producto'].widget = forms.HiddenInput()
        form.fields['tipo'].widget = forms.HiddenInput()
        return render(request, self.template_name, {'form': form, 'tipo_descuento': descuento})

    def post(self, request, tipo):
        descuento = get_object_or_404(TipoDescuento, tipo=tipo)
        form = ProductoDescuentoCreateForm(
            request.POST,
            initial={'aplica_a': ProductoDescuentoCreateForm.APLICA_TIPO, 'tipo': descuento.tipo}
        )
        form.fields['aplica_a'].widget = forms.HiddenInput()
        form.fields['producto'].widget = forms.HiddenInput()
        form.fields['tipo'].widget = forms.HiddenInput()
        if form.is_valid():
            form.save()
            messages.success(request, 'Descuento actualizado.')
            return redirect('inventario:producto_descuentos')
        return render(request, self.template_name, {'form': form, 'tipo_descuento': descuento})


class TipoDescuentoDisableView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_producto'

    def post(self, request, tipo):
        descuento = get_object_or_404(TipoDescuento, tipo=tipo)
        descuento.descuento_pct = 0
        descuento.descuento_desde = None
        descuento.descuento_hasta = None
        descuento.save(update_fields=['descuento_pct', 'descuento_desde', 'descuento_hasta'])
        messages.success(request, 'Descuento desactivado.')
        return redirect('inventario:producto_descuentos')


class ProductoDescuentoDisableView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_producto'

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto.descuento_pct = 0
        producto.descuento_desde = None
        producto.descuento_hasta = None
        producto.save(update_fields=['descuento_pct', 'descuento_desde', 'descuento_hasta'])
        messages.success(request, 'Descuento desactivado.')
        return redirect('inventario:producto_descuentos')


class VentaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Venta
    form_class = VentaForm
    template_name = 'inventario/venta_form.html'
    success_url = reverse_lazy('inventario:venta_list')
    permission_required = 'inventario.add_venta'

    def get(self, request, *args, **kwargs):
        config = get_venta_config()
        form = self.form_class(user=request.user, config=config)
        formset = VentaItemFormSet(queryset=SaleItem.objects.none(), initial=[{}])
        products_map = build_products_map()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'products_json': json.dumps(products_map, default=str),
            'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
            'iva_rate': str(config.iva_rate),
        })

    def post(self, request, *args, **kwargs):
        config = get_venta_config()
        form = self.form_class(request.POST, user=request.user, config=config)
        formset = VentaItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                venta = form.save(commit=False)
                is_admin_role = request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser
                if not is_admin_role:
                    staff_profile = getattr(request.user, 'staff_profile', None)
                    if staff_profile:
                        venta.vendedor = staff_profile
                venta.created_by = request.user if request.user.is_authenticated else None
                venta.updated_by = request.user if request.user.is_authenticated else None
                venta.save()
                formset.instance = venta
                formset.save()
                today = timezone.localdate()
                tipo_desc_map = _get_tipo_descuentos_map()
                allow_manual = config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser)
                for item in venta.items.select_related('producto').all():
                    prod = item.producto
                    pct = None
                    if prod:
                        if prod.descuento_activo(today):
                            pct = float(prod.descuento_pct or 0)
                        else:
                            tipo_desc = tipo_desc_map.get(prod.tipo)
                            if tipo_desc and tipo_desc.descuento_activo(today):
                                pct = float(tipo_desc.descuento_pct or 0)
                    if pct is not None and pct > 0:
                        item.descuento = round(float(item.cantidad) * float(item.precio_unitario) * pct / 100, 2)
                        item.save(update_fields=['descuento'])
                    elif not allow_manual:
                        if item.descuento:
                            item.descuento = 0
                            item.save(update_fields=['descuento'])
                if not config.descuento_habilitado:
                    venta.descuento_global = 0
                subtotal = sum(item.subtotal for item in venta.items.all())
                base_total = Decimal(str(subtotal)) - Decimal(str(venta.descuento_global or 0))
                if base_total < 0:
                    base_total = Decimal('0')
                if venta.iva_rate_aplicado is None:
                    venta.iva_rate_aplicado = Decimal(str(config.iva_rate or 0))
                rate = Decimal(str(venta.iva_rate_aplicado or 0))
                if rate > 0:
                    base_sin_iva = (base_total / (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    venta.impuesto = (base_total - base_sin_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    venta.impuesto = Decimal('0.00')
                venta.save(update_fields=['descuento_global', 'impuesto', 'iva_rate_aplicado'])
                from .models import recalc_venta_total
                recalc_venta_total(venta)
                if venta.estado == Venta.ESTADO_PAGADA:
                    try:
                        venta.apply_stock_changes()
                    except ValueError as e:
                        form.add_error(None, str(e))
                        transaction.set_rollback(True)
                        products_map = build_products_map()
                        return render(request, self.template_name, {
                            'form': form,
                            'formset': formset,
                            'products_json': json.dumps(products_map, default=str),
                            'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
                            'iva_rate': str(config.iva_rate),
                        })
                VentaAudit.objects.create(
                    venta=venta,
                    user=request.user if request.user.is_authenticated else None,
                    action='created',
                    notes='Creación desde interfaz'
                )
            return redirect('inventario:venta_detail', pk=venta.pk)
        products_map = build_products_map()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'products_json': json.dumps(products_map, default=str),
            'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
            'iva_rate': str(config.iva_rate),
        })


class VentaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Venta
    template_name = 'inventario/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 20
    permission_required = 'inventario.view_venta'

    def get_queryset(self):
        qs = Venta.objects.select_related('id_propietario', 'vendedor').all()
        q = self.request.GET.get('q')
        vendedor = self.request.GET.get('vendedor')
        fecha_from = self.request.GET.get('from')
        fecha_to = self.request.GET.get('to')
        if q:
            q_filter = (
                Q(notas__icontains=q) |
                Q(id_propietario__username__icontains=q) |
                Q(id_propietario__first_name__icontains=q) |
                Q(id_propietario__last_name__icontains=q) |
                Q(vendedor__nombre_completo__icontains=q)
            )
            if q.isdigit():
                q_filter = q_filter | Q(id=int(q))
            qs = qs.filter(q_filter)
        if vendedor:
            qs = qs.filter(vendedor__id=vendedor)
        if fecha_from:
            qs = qs.filter(fecha__date__gte=fecha_from)
        if fecha_to:
            qs = qs.filter(fecha__date__lte=fecha_to)
        return qs.order_by('-fecha')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_admin = user.groups.filter(name='ADMIN').exists() or user.is_superuser
        context['is_admin'] = is_admin
        ventas = context.get('ventas') or []
        venta_ids = [v.id for v in ventas]
        pending_ids = set(
            SolicitudAnulacionVenta.objects.filter(
                venta_id__in=venta_ids,
                estado=SolicitudAnulacionVenta.ESTADO_PENDIENTE
            ).values_list('venta_id', flat=True)
        )
        context['pending_anulaciones'] = pending_ids
        return context


class VentaConfigUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'inventario/venta_config.html'
    permission_required = 'inventario.change_ventaconfig'

    def get(self, request):
        config = get_venta_config()
        form = VentaConfigForm(instance=config)
        return render(request, self.template_name, {'form': form, 'config': config})

    def post(self, request):
        config = get_venta_config()
        iva_quick = request.POST.get('iva_quick')
        if iva_quick:
            config.iva_rate = Decimal(str(iva_quick))
            config.save(update_fields=['iva_rate'])
            messages.success(request, 'IVA actualizado.')
            return redirect('inventario:venta_config')
        form = VentaConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'ConfiguraciÃ³n de ventas actualizada.')
            return redirect('inventario:venta_config')
        return render(request, self.template_name, {'form': form, 'config': config})


class VentaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Venta
    template_name = 'inventario/venta_detail.html'
    context_object_name = 'venta'
    permission_required = 'inventario.view_venta'

    def get_queryset(self):
        return Venta.objects.select_related('id_propietario', 'vendedor').prefetch_related('items__producto')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        venta = ctx.get('venta')
        if venta:
            ctx['descuento_items'] = sum(item.descuento or 0 for item in venta.items.all())
        return ctx


class VentaReceiptView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Venta
    template_name = 'inventario/venta_receipt.html'
    context_object_name = 'venta'
    permission_required = 'inventario.view_venta'

    def get_queryset(self):
        return Venta.objects.select_related('id_propietario', 'vendedor').prefetch_related('items__producto')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        venta = ctx.get('venta')
        if not venta:
            return ctx

        items = list(venta.items.all())
        line_items = []
        subtotal_bruto = 0
        descuento_items = 0
        subtotal_neto = 0
        for item in items:
            bruto = (item.cantidad or 0) * (item.precio_unitario or 0)
            desc = item.descuento or 0
            neto = item.subtotal
            precio_final = (neto / item.cantidad) if item.cantidad else item.precio_unitario
            line_items.append({
                'item': item,
                'subtotal_bruto': bruto,
                'descuento': desc,
                'precio_final': precio_final,
            })
            subtotal_bruto += bruto
            descuento_items += desc
            subtotal_neto += neto

        ctx['audits'] = VentaAudit.objects.filter(venta=venta).select_related('user').order_by('-timestamp')[:10]
        ctx['line_items'] = line_items
        ctx['subtotal_bruto'] = subtotal_bruto
        ctx['descuento_items'] = descuento_items
        ctx['subtotal_neto'] = subtotal_neto
        return ctx

    def has_permission(self):
        if self.request.user.has_perm(self.permission_required):
            return True
        try:
            venta = self.get_object()
        except Exception:
            return False
        owner = getattr(venta, 'id_propietario', None)
        owner_user_id = getattr(owner, 'user_id', None)
        if owner_user_id == self.request.user.id:
            return True
        vendedor = getattr(venta, 'vendedor', None)
        vendedor_user_id = getattr(vendedor, 'user_id', None)
        return vendedor_user_id == self.request.user.id


class VentaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'inventario/venta_form.html'
    form_class = VentaForm
    permission_required = 'inventario.change_venta'

    def dispatch(self, request, *args, **kwargs):
        messages.warning(request, 'La edición de ventas está deshabilitada por seguridad.')
        pk = kwargs.get('pk')
        if pk:
            return redirect('inventario:venta_detail', pk=pk)
        return redirect('inventario:venta_list')

    def get(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        config = get_venta_config()
        form = self.form_class(instance=venta, user=request.user, config=config)
        formset = VentaItemFormSet(instance=venta)
        products_map = build_products_map()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'object': venta,
            'products_json': json.dumps(products_map, default=str),
            'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
            'iva_rate': str(config.iva_rate),
        })

    def post(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        prev_estado = venta.estado
        config = get_venta_config()
        form = self.form_class(request.POST, instance=venta, user=request.user, config=config)
        formset = VentaItemFormSet(request.POST, instance=venta)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Enforce: only ADMIN can set ANULADA
                if form.instance.estado == Venta.ESTADO_ANULADA:
                    is_admin = request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser
                    if not is_admin:
                        form.add_error('estado', 'Solo un administrador puede anular una venta.')
                        products_map = build_products_map()
                        return render(request, self.template_name, {
                            'form': form,
                            'formset': formset,
                            'object': venta,
                            'products_json': json.dumps(products_map, default=str),
                            'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
                            'iva_rate': str(config.iva_rate),
                        })
                is_admin_role = request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser
                if not is_admin_role:
                    staff_profile = getattr(request.user, 'staff_profile', None)
                    if staff_profile:
                        form.instance.vendedor = staff_profile
                form.save()
                formset.save()
                today = timezone.localdate()
                tipo_desc_map = _get_tipo_descuentos_map()
                allow_manual = config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser)
                for item in venta.items.select_related('producto').all():
                    prod = item.producto
                    pct = None
                    if prod:
                        if prod.descuento_activo(today):
                            pct = float(prod.descuento_pct or 0)
                        else:
                            tipo_desc = tipo_desc_map.get(prod.tipo)
                            if tipo_desc and tipo_desc.descuento_activo(today):
                                pct = float(tipo_desc.descuento_pct or 0)
                    if pct is not None and pct > 0:
                        item.descuento = round(float(item.cantidad) * float(item.precio_unitario) * pct / 100, 2)
                        item.save(update_fields=['descuento'])
                    elif not allow_manual:
                        if item.descuento:
                            item.descuento = 0
                            item.save(update_fields=['descuento'])
                if not config.descuento_habilitado:
                    venta.descuento_global = 0
                subtotal = sum(item.subtotal for item in venta.items.all())
                base_total = Decimal(str(subtotal)) - Decimal(str(venta.descuento_global or 0))
                if base_total < 0:
                    base_total = Decimal('0')
                if venta.iva_rate_aplicado is None:
                    venta.iva_rate_aplicado = Decimal(str(config.iva_rate or 0))
                rate = Decimal(str(venta.iva_rate_aplicado or 0))
                if rate > 0:
                    base_sin_iva = (base_total / (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    venta.impuesto = (base_total - base_sin_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    venta.impuesto = Decimal('0.00')
                venta.save(update_fields=['descuento_global', 'impuesto', 'iva_rate_aplicado'])
                from .models import recalc_venta_total
                recalc_venta_total(venta)
                try:
                    if prev_estado == Venta.ESTADO_PAGADA and venta.estado in (Venta.ESTADO_ANULADA, Venta.ESTADO_BORRADOR):
                        venta.revert_stock_changes()
                    elif prev_estado in (Venta.ESTADO_ANULADA, Venta.ESTADO_BORRADOR) and venta.estado == Venta.ESTADO_PAGADA:
                        if not venta.stock_committed:
                            venta.apply_stock_changes()
                    elif venta.estado == Venta.ESTADO_PAGADA:
                        if not venta.stock_committed:
                            venta.apply_stock_changes()
                except ValueError as e:
                    form.add_error(None, str(e))
                    transaction.set_rollback(True)
                    products_map = build_products_map()
                    return render(request, self.template_name, {
                        'form': form,
                        'formset': formset,
                        'object': venta,
                        'products_json': json.dumps(products_map, default=str),
                        'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
                        'iva_rate': str(config.iva_rate),
                    })
                VentaAudit.objects.create(
                    venta=venta,
                    user=request.user if request.user.is_authenticated else None,
                    action='updated',
                    notes='Actualización desde interfaz'
                )
            return redirect('inventario:venta_detail', pk=venta.pk)
        products_map = build_products_map()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'object': venta,
            'products_json': json.dumps(products_map, default=str),
            'allow_descuento': config.descuento_habilitado and (request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser),
            'iva_rate': str(config.iva_rate),
        })


class VentaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Venta
    template_name = 'inventario/venta_confirm_delete.html'
    success_url = reverse_lazy('inventario:venta_list')
    permission_required = 'inventario.delete_venta'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        VentaAudit.objects.create(venta=self.object, user=request.user if request.user.is_authenticated else None, action='deleted', notes='Eliminación desde interfaz')
        return super().delete(request, *args, **kwargs)


@login_required
@permission_required('inventario.view_producto', raise_exception=True)
def product_autocomplete(request):
    q = request.GET.get('q', '').strip()
    config = get_venta_config()
    rate = Decimal(str(config.iva_rate or 0))
    qs = Producto.objects.filter(is_active=True)
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    qs = qs.order_by('nombre')[:20]
    data = [{
        'id': p.id,
        'nombre': p.nombre,
        'precio': str((Decimal(str(p.precio or 0)) * (Decimal('1') + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        'precio_base': str(p.precio),
        'stock': p.stock_inicial,
        'tipo': p.tipo,
        'lote': p.lote or '',
        'vencimiento': p.fecha_vencimiento.isoformat() if p.fecha_vencimiento else ''
    } for p in qs]
    return JsonResponse({'results': data})


class VentaAuditListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = VentaAudit
    template_name = 'inventario/venta_audit_list.html'
    context_object_name = 'audits'
    paginate_by = 50
    permission_required = 'inventario.view_ventaaudit'

    def get_queryset(self):
        qs = VentaAudit.objects.select_related('user', 'venta').all()
        user = self.request.GET.get('user')
        action = self.request.GET.get('action')
        fecha_from = self.request.GET.get('from')
        fecha_to = self.request.GET.get('to')
        if user:
            qs = qs.filter(user__username__icontains=user)
        if action:
            qs = qs.filter(action=action)
        if fecha_from:
            qs = qs.filter(timestamp__date__gte=fecha_from)
        if fecha_to:
            qs = qs.filter(timestamp__date__lte=fecha_to)
        return qs.order_by('-timestamp')

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('export') == 'csv':
            qs = self.get_queryset()
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename="venta_audit.csv"'
            writer = csv.writer(resp)
            writer.writerow(['id', 'venta_id', 'user', 'action', 'timestamp', 'notes'])
            for a in qs:
                writer.writerow([a.id, a.venta_id, a.user.username if a.user else '', a.action, a.timestamp.isoformat(), a.notes])
            return resp
        return super().render_to_response(context, **response_kwargs)


class SolicitudAnulacionCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.add_solicitudanulacionventa'

    def post(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        if venta.estado == Venta.ESTADO_ANULADA:
            messages.warning(request, 'La venta ya estÃ¡ anulada.')
            return redirect('inventario:venta_list')
        motivo = (request.POST.get('motivo') or '').strip()
        if not motivo:
            messages.error(request, 'El motivo de anulación es obligatorio.')
            return redirect('inventario:venta_list')
        existing = SolicitudAnulacionVenta.objects.filter(
            venta=venta,
            estado=SolicitudAnulacionVenta.ESTADO_PENDIENTE
        ).first()
        if existing:
            messages.info(request, 'Ya existe una solicitud de anulación pendiente para esta venta.')
            return redirect('inventario:venta_list')
        SolicitudAnulacionVenta.objects.create(
            venta=venta,
            solicitado_por=request.user if request.user.is_authenticated else None,
            motivo=motivo
        )
        messages.success(request, 'Solicitud de anulación enviada al administrador.')
        return redirect('inventario:venta_list')


class SolicitudAnulacionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = SolicitudAnulacionVenta
    template_name = 'inventario/anulacion_list.html'
    context_object_name = 'solicitudes'
    paginate_by = 20
    permission_required = 'inventario.view_solicitudanulacionventa'

    def get_queryset(self):
        qs = SolicitudAnulacionVenta.objects.select_related('venta', 'solicitado_por').all()
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class SolicitudAnulacionApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_solicitudanulacionventa'

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudAnulacionVenta, pk=pk)
        if solicitud.estado != SolicitudAnulacionVenta.ESTADO_PENDIENTE:
            return redirect('inventario:anulacion_list')
        venta = solicitud.venta
        solicitud.estado = SolicitudAnulacionVenta.ESTADO_APROBADA
        solicitud.resolved_at = timezone.now()
        solicitud.save(update_fields=['estado', 'resolved_at'])

        if venta.estado != Venta.ESTADO_ANULADA:
            prev_estado = venta.estado
            venta.estado = Venta.ESTADO_ANULADA
            venta.save(update_fields=['estado'])
            if prev_estado == Venta.ESTADO_PAGADA:
                venta.revert_stock_changes()
            VentaAudit.objects.create(
                venta=venta,
                user=request.user if request.user.is_authenticated else None,
                action='anulacion_aprobada',
                notes='Anulación aprobada desde solicitudes'
            )
        messages.success(request, 'Anulación aprobada.')
        return redirect('inventario:anulacion_list')


class SolicitudAnulacionRejectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_solicitudanulacionventa'

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudAnulacionVenta, pk=pk)
        if solicitud.estado != SolicitudAnulacionVenta.ESTADO_PENDIENTE:
            return redirect('inventario:anulacion_list')
        solicitud.estado = SolicitudAnulacionVenta.ESTADO_RECHAZADA
        solicitud.resolved_at = timezone.now()
        solicitud.save(update_fields=['estado', 'resolved_at'])
        VentaAudit.objects.create(
            venta=solicitud.venta,
            user=request.user if request.user.is_authenticated else None,
            action='anulacion_rechazada',
            notes='Anulación rechazada desde solicitudes'
        )
        messages.info(request, 'Solicitud rechazada.')
        return redirect('inventario:anulacion_list')


class RecordatorioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Recordatorio
    template_name = 'inventario/recordatorio_list.html'
    context_object_name = 'recordatorios'
    paginate_by = 20
    permission_required = 'inventario.view_recordatorio'

    def get_queryset(self):
        qs = Recordatorio.objects.select_related('producto').all()
        estado = self.request.GET.get('estado')
        tipo = self.request.GET.get('tipo')
        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs.order_by('fecha')


class RecordatorioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Recordatorio
    form_class = RecordatorioForm
    template_name = 'inventario/recordatorio_form.html'
    success_url = reverse_lazy('inventario:recordatorio_list')
    permission_required = 'inventario.add_recordatorio'

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.save()
        return super().form_valid(form)


class RecordatorioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Recordatorio
    form_class = RecordatorioForm
    template_name = 'inventario/recordatorio_form.html'
    success_url = reverse_lazy('inventario:recordatorio_list')
    permission_required = 'inventario.change_recordatorio'


class RecordatorioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Recordatorio
    template_name = 'inventario/recordatorio_confirm_delete.html'
    success_url = reverse_lazy('inventario:recordatorio_list')
    permission_required = 'inventario.delete_recordatorio'


class RecordatorioCompleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_recordatorio'

    def post(self, request, pk):
        recordatorio = get_object_or_404(Recordatorio, pk=pk)
        recordatorio.estado = Recordatorio.ESTADO_COMPLETADO
        recordatorio.save(update_fields=['estado'])
        return redirect('inventario:recordatorio_list')


class InventoryMovementListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = InventoryMovement
    template_name = 'inventario/kardex_list.html'
    context_object_name = 'movimientos'
    paginate_by = 50
    permission_required = 'inventario.view_inventorymovement'

    def get_queryset(self):
        qs = InventoryMovement.objects.select_related('producto', 'created_by').all()
        producto = self.request.GET.get('producto')
        tipo = self.request.GET.get('tipo')
        fecha_from = self.request.GET.get('from')
        fecha_to = self.request.GET.get('to')
        user = self.request.GET.get('user')
        if producto:
            qs = qs.filter(producto_id=producto)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if user:
            qs = qs.filter(created_by_id=user)
        if fecha_from:
            qs = qs.filter(created_at__date__gte=fecha_from)
        if fecha_to:
            qs = qs.filter(created_at__date__lte=fecha_to)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['productos'] = Producto.objects.filter(is_active=True).order_by('nombre')
        ctx['tipo_choices'] = InventoryMovement.TIPO_CHOICES
        ctx['usuarios'] = list(
            InventoryMovement.objects.exclude(created_by__isnull=True)
            .values_list('created_by__id', 'created_by__username')
            .distinct()
            .order_by('created_by__username')
        )
        movimientos = ctx.get('movimientos')
        if movimientos:
            ajuste_ids = set()
            for m in movimientos:
                if m.tipo == InventoryMovement.TIPO_AJUSTE and m.referencia and 'Ajuste #' in m.referencia:
                    try:
                        ajuste_id = int(m.referencia.split('Ajuste #')[-1].strip().split()[0])
                        ajuste_ids.add(ajuste_id)
                        m._ajuste_id = ajuste_id
                    except ValueError:
                        m._ajuste_id = None
            if ajuste_ids:
                ajustes = StockAdjustmentRequest.objects.select_related('solicitado_por', 'aprobado_por').filter(id__in=ajuste_ids)
                ajuste_map = {a.id: a for a in ajustes}
                for m in movimientos:
                    aid = getattr(m, '_ajuste_id', None)
                    if aid and aid in ajuste_map:
                        a = ajuste_map[aid]
                        m.ajuste_solicitado_por = a.solicitado_por.get_full_name() if a.solicitado_por and a.solicitado_por.get_full_name() else (a.solicitado_por.username if a.solicitado_por else '-')
                        m.ajuste_aprobado_por = a.aprobado_por.get_full_name() if a.aprobado_por and a.aprobado_por.get_full_name() else (a.aprobado_por.username if a.aprobado_por else '-')
                    else:
                        m.ajuste_solicitado_por = '-'
                        m.ajuste_aprobado_por = '-'
            else:
                for m in movimientos:
                    m.ajuste_solicitado_por = '-'
                    m.ajuste_aprobado_por = '-'
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('export') == 'csv':
            qs = self.get_queryset()
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename=\"kardex.csv\"'
            writer = csv.writer(resp)
            writer.writerow(['fecha', 'producto', 'tipo', 'cantidad', 'stock_before', 'stock_after', 'lote', 'vencimiento', 'referencia', 'usuario'])
            for m in qs:
                writer.writerow([
                    m.created_at.isoformat(),
                    m.producto.nombre,
                    m.get_tipo_display(),
                    m.cantidad,
                    m.stock_before,
                    m.stock_after,
                    m.lote,
                    m.fecha_vencimiento.isoformat() if m.fecha_vencimiento else '',
                    m.referencia,
                    m.created_by.username if m.created_by else '',
                ])
            return resp
        return super().render_to_response(context, **response_kwargs)


class ReportesView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.view_venta'
    template_name = 'inventario/reportes.html'

    def dispatch(self, request, *args, **kwargs):
        is_admin = request.user.groups.filter(name='ADMIN').exists() or request.user.is_superuser
        if not is_admin:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        ventas = Venta.objects.filter(estado=Venta.ESTADO_PAGADA)
        fecha_from = request.GET.get('from')
        fecha_to = request.GET.get('to')
        if fecha_from:
            ventas = ventas.filter(fecha__date__gte=fecha_from)
        if fecha_to:
            ventas = ventas.filter(fecha__date__lte=fecha_to)

        ingreso_expr = ExpressionWrapper(
            (F('cantidad') * F('precio_unitario')) - F('descuento'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        utilidad_expr = ExpressionWrapper(
            ((F('precio_unitario') - Coalesce(F('costo_unitario'), F('producto__costo_compra'))) * F('cantidad')) - F('descuento'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )

        items = SaleItem.objects.filter(venta__in=ventas)

        total_ventas = ventas.aggregate(total=Coalesce(Sum('total'), Value(0)))['total']
        ventas_por_metodo = list(
            ventas.values('metodo_pago')
            .annotate(total=Coalesce(Sum('total'), Value(0)), count=Count('id'))
            .order_by('-total')
        )
        ventas_por_vendedor = list(
            ventas.values('vendedor__nombre_completo')
            .annotate(total=Coalesce(Sum('total'), Value(0)), count=Count('id'))
            .order_by('-total')
        )
        top_productos = list(
            items.values('producto__nombre')
            .annotate(qty=Coalesce(Sum('cantidad'), Value(0)),
                      ingreso=Coalesce(Sum(ingreso_expr), Value(0)),
                      utilidad=Coalesce(Sum(utilidad_expr), Value(0)))
            .order_by('-ingreso')[:10]
        )
        bottom_productos = list(
            items.values('producto__nombre')
            .annotate(qty=Coalesce(Sum('cantidad'), Value(0)),
                      ingreso=Coalesce(Sum(ingreso_expr), Value(0)))
            .order_by('qty')[:10]
        )
        ventas_por_categoria = list(
            items.values('producto__categoria__name')
            .annotate(qty=Coalesce(Sum('cantidad'), Value(0)),
                      ingreso=Coalesce(Sum(ingreso_expr), Value(0)))
            .order_by('-ingreso')
        )
        ventas_por_dia = list(
            ventas.values('fecha__date')
            .annotate(total=Coalesce(Sum('total'), Value(0)), count=Count('id'))
            .order_by('fecha__date')
        )

        if request.GET.get('export') == 'csv':
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = 'attachment; filename="reporte_ventas.csv"'
            writer = csv.writer(resp)
            writer.writerow(['venta_id', 'fecha', 'cliente', 'vendedor', 'metodo', 'total'])
            for v in ventas.select_related('id_propietario', 'vendedor'):
                if v.id_propietario:
                    cliente = v.id_propietario.get_full_name() or v.id_propietario.username
                else:
                    cliente = v.cliente_nombre
                writer.writerow([
                    v.id,
                    v.fecha.isoformat(),
                    cliente,
                    v.vendedor.nombre_completo if v.vendedor else '',
                    v.get_metodo_pago_display(),
                    v.total
                ])
            return resp

        return render(request, self.template_name, {
            'total_ventas': total_ventas,
            'ventas_por_metodo': ventas_por_metodo,
            'ventas_por_vendedor': ventas_por_vendedor,
            'top_productos': top_productos,
            'bottom_productos': bottom_productos,
            'ventas_por_categoria': ventas_por_categoria,
            'ventas_por_dia': ventas_por_dia,
        })


class LotesVencerListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ProductoLote
    template_name = 'inventario/lotes_vencer.html'
    context_object_name = 'lotes'
    paginate_by = 50
    permission_required = 'inventario.view_productolote'

    def get_queryset(self):
        days = int(self.request.GET.get('dias') or 30)
        limite = timezone.now().date() + timedelta(days=days)
        qs = ProductoLote.objects.select_related('producto').filter(
            cantidad__gt=0,
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=limite,
            producto__is_active=True,
            producto__tipo=Producto.TIPO_MEDICAMENTO,
        )
        return qs.order_by('fecha_vencimiento', 'producto__nombre')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['dias'] = int(self.request.GET.get('dias') or 30)
        return ctx


class StockAdjustmentRequestListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = StockAdjustmentRequest
    template_name = 'inventario/ajuste_list.html'
    context_object_name = 'ajustes'
    paginate_by = 20
    permission_required = 'inventario.view_stockadjustmentrequest'

    def get_queryset(self):
        qs = StockAdjustmentRequest.objects.select_related('producto', 'solicitado_por', 'aprobado_por').all()
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        if is_owner_only(self.request.user):
            qs = qs.filter(solicitado_por=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_admin'] = self.request.user.groups.filter(name='ADMIN').exists() or self.request.user.is_superuser
        return ctx


class StockAdjustmentRequestCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = StockAdjustmentRequest
    form_class = StockAdjustmentRequestForm
    template_name = 'inventario/ajuste_form.html'
    success_url = reverse_lazy('inventario:ajuste_list')
    permission_required = 'inventario.add_stockadjustmentrequest'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.solicitado_por = self.request.user
        self.object.save()
        messages.success(self.request, 'Solicitud de ajuste creada y enviada para aprobación.')
        return redirect(self.success_url)


class StockAdjustmentApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_stockadjustmentrequest'

    def post(self, request, pk):
        ajuste = get_object_or_404(StockAdjustmentRequest, pk=pk)
        if ajuste.estado != StockAdjustmentRequest.ESTADO_PENDIENTE:
            return redirect('inventario:ajuste_list')
        prod = ajuste.producto
        if prod.tipo == Producto.TIPO_SERVICIO:
            messages.error(request, 'No se puede ajustar stock de servicios.')
            return redirect('inventario:ajuste_list')
        before = prod.stock_inicial
        if prod.tipo == Producto.TIPO_MEDICAMENTO:
            lote, _ = ProductoLote.objects.get_or_create(
                producto=prod,
                lote=ajuste.lote or 'SIN-LOTE',
                fecha_vencimiento=ajuste.fecha_vencimiento,
                defaults={'cantidad': 0},
            )
            if ajuste.cantidad < 0 and lote.cantidad < abs(ajuste.cantidad):
                messages.error(request, 'No hay suficiente cantidad en ese lote para el ajuste.')
                return redirect('inventario:ajuste_list')
            lote.cantidad += ajuste.cantidad
            if lote.cantidad < 0:
                messages.error(request, 'No se puede aprobar: el ajuste dejaría el lote en negativo.')
                return redirect('inventario:ajuste_list')
            lote.save(update_fields=['cantidad'])
            prod.stock_inicial = sum(l.cantidad for l in prod.lotes.all())
            if ajuste.lote:
                prod.lote = ajuste.lote
            if ajuste.fecha_vencimiento:
                prod.fecha_vencimiento = ajuste.fecha_vencimiento
            prod.save(update_fields=['stock_inicial', 'lote', 'fecha_vencimiento'])
            after = prod.stock_inicial
        else:
            after = before + ajuste.cantidad
            if after < 0:
                messages.error(request, 'No se puede aprobar: el ajuste dejaría el stock en negativo.')
                return redirect('inventario:ajuste_list')
            prod.stock_inicial = after
            prod.save(update_fields=['stock_inicial'])
        InventoryMovement.objects.create(
            producto=prod,
            tipo=InventoryMovement.TIPO_AJUSTE,
            cantidad=ajuste.cantidad,
            stock_before=before,
            stock_after=after,
            lote=ajuste.lote or prod.lote,
            fecha_vencimiento=ajuste.fecha_vencimiento or prod.fecha_vencimiento,
            referencia=f"Ajuste #{ajuste.id}",
            created_by=request.user if request.user.is_authenticated else None,
        )
        ajuste.estado = StockAdjustmentRequest.ESTADO_APROBADA
        ajuste.aprobado_por = request.user
        ajuste.resolved_at = timezone.now()
        ajuste.save(update_fields=['estado', 'aprobado_por', 'resolved_at'])
        messages.success(request, 'Ajuste aprobado y aplicado.')
        return redirect('inventario:ajuste_list')


class StockAdjustmentRejectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventario.change_stockadjustmentrequest'

    def post(self, request, pk):
        ajuste = get_object_or_404(StockAdjustmentRequest, pk=pk)
        if ajuste.estado != StockAdjustmentRequest.ESTADO_PENDIENTE:
            return redirect('inventario:ajuste_list')
        ajuste.estado = StockAdjustmentRequest.ESTADO_RECHAZADA
        ajuste.aprobado_por = request.user
        ajuste.resolved_at = timezone.now()
        ajuste.save(update_fields=['estado', 'aprobado_por', 'resolved_at'])
        messages.info(request, 'Solicitud rechazada.')
        return redirect('inventario:ajuste_list')
