from django import forms
from .models import Venta, Recordatorio, VentaConfig
from usuarios.models import Staff


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        # fecha es auto_now_add en el modelo; no es editable desde el formulario
        fields = ['id_propietario', 'cliente_nombre', 'vendedor', 'metodo_pago', 'estado', 'descuento_global', 'impuesto', 'notas']
        widgets = {
            'id_propietario': forms.Select(attrs={'class': 'form-select'}),
            'cliente_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente (si no tiene usuario)'}),
            'vendedor': forms.Select(attrs={'class': 'form-select'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'descuento_global': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        config = kwargs.pop('config', None)
        self._user = user
        super().__init__(*args, **kwargs)
        # Tax is configured globally; hide from sales form
        if 'impuesto' in self.fields:
            self.fields.pop('impuesto')
        # Show full name in cliente dropdown; allow empty selection
        field = self.fields.get('id_propietario')
        if field:
            field.required = False
            field.empty_label = ''
            field.label_from_instance = lambda obj: obj.get_full_name() or obj.username
        estado_field = self.fields.get('estado')
        if estado_field and user:
            is_admin_role = user.groups.filter(name='ADMIN').exists() or user.is_superuser
            if not is_admin_role:
                estado_field.choices = [
                    (Venta.ESTADO_BORRADOR, 'Borrador'),
                    (Venta.ESTADO_PAGADA, 'Pagada'),
                ]
        # Only ADMIN can edit global discount and only if enabled in config
        descuento_field = self.fields.get('descuento_global')
        if descuento_field:
            is_admin_role = bool(user and (user.groups.filter(name='ADMIN').exists() or user.is_superuser))
            if not (is_admin_role and config and config.descuento_habilitado):
                self.fields.pop('descuento_global')
        # Limit vendedor to logged-in staff user
        vendedor_field = self.fields.get('vendedor')
        if vendedor_field and user:
            is_admin_role = user.groups.filter(name='ADMIN').exists() or user.is_superuser
            # Use Staff profiles only; don't exclude by DUENO to avoid hiding multi-rol users.
            base_qs = Staff.objects.filter(is_active=True)
            if is_admin_role:
                vendedor_field.queryset = base_qs
            else:
                staff_profile = getattr(user, 'staff_profile', None)
                if staff_profile:
                    vendedor_field.queryset = base_qs.filter(pk=staff_profile.pk)
                    vendedor_field.initial = staff_profile.pk
                else:
                    # Fallback: allow selecting any active staff if no profile is linked.
                    vendedor_field.queryset = base_qs

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('id_propietario'):
            cleaned['cliente_nombre'] = ''
        descuento = cleaned.get('descuento_global') or 0
        if descuento < 0:
            self.add_error('descuento_global', 'El descuento no puede ser negativo.')
        return cleaned


class VentaConfigForm(forms.ModelForm):
    class Meta:
        model = VentaConfig
        fields = ['descuento_habilitado', 'iva_rate']
        widgets = {
            'descuento_habilitado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'iva_rate': forms.Select(attrs={'class': 'form-select'}),
        }

from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import SaleItem, Producto


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento', 'lote']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BaseSaleItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        has_item = False
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            producto = form.cleaned_data.get('producto')
            cantidad = form.cleaned_data.get('cantidad')
            precio = form.cleaned_data.get('precio_unitario')
            if producto and cantidad and precio:
                has_item = True
            elif producto or cantidad or precio:
                # Partially filled row
                raise forms.ValidationError('Completa producto, cantidad y precio en cada ítem.')
        if not has_item:
            raise forms.ValidationError('Agrega al menos un producto a la venta.')


VentaItemFormSet = inlineformset_factory(
    Venta,
    SaleItem,
    form=SaleItemForm,
    formset=BaseSaleItemFormSet,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
from django import forms
from .models import Producto, Categoria, StockAdjustmentRequest, TipoDescuento


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre',
            'categoria',
            'tipo',
            'codigo',
            'presentacion',
            'contenido',
            'unidad_contenido',
            'lote',
            'fecha_vencimiento',
            'proveedor',
            'stock_inicial',
            'stock_minimo',
            'costo_compra',
            'precio',
            'descuento_pct',
            'descuento_desde',
            'descuento_hasta',
            'descripcion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Collar para perros'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código o SKU'}),
            'presentacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Caja, frasco, bl?ster'}),
            'contenido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'unidad_contenido': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lote del producto'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'proveedor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proveedor o laboratorio'}),
            'stock_inicial': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'costo_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'descuento_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'descuento_desde': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descuento_hasta': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self._user = user
        super().__init__(*args, **kwargs)
        is_admin = bool(user and (user.groups.filter(name='ADMIN').exists() or user.is_superuser))
        if not is_admin:
            for f in ['descuento_pct', 'descuento_desde', 'descuento_hasta']:
                self.fields.pop(f, None)
        fecha_field = self.fields.get('fecha_vencimiento')
        if fecha_field:
            fecha_field.input_formats = ['%Y-%m-%d']
        if fecha_field and self.instance and self.instance.pk and self.instance.fecha_vencimiento:
            fecha_field.initial = self.instance.fecha_vencimiento.isoformat()
        if user and not is_admin:
            if not user.has_perm('inventario.change_producto_stock'):
                for name in ['stock_inicial', 'stock_minimo']:
                    if name in self.fields:
                        self.fields[name].disabled = True
            if self.instance and self.instance.pk:
                if not user.has_perm('inventario.change_producto_precio'):
                    if 'precio' in self.fields:
                        self.fields['precio'].disabled = True
                        self.fields['precio'].help_text = 'Solo Admin puede modificar este valor.'
                if not user.has_perm('inventario.change_producto_costo'):
                    if 'costo_compra' in self.fields:
                        self.fields['costo_compra'].disabled = True
                        self.fields['costo_compra'].help_text = 'Solo Admin puede modificar este valor.'
            if not user.has_perm('inventario.change_producto_lote'):
                for name in ['lote', 'fecha_vencimiento']:
                    if name in self.fields:
                        self.fields[name].disabled = True
        if self.is_bound:
            for name, field in self.fields.items():
                if self.errors.get(name):
                    classes = field.widget.attrs.get('class', '')
                    if 'is-invalid' not in classes:
                        field.widget.attrs['class'] = f"{classes} is-invalid".strip()

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None or precio < 0:
            raise forms.ValidationError('Ingrese un precio v?lido.')
        return precio

    def clean_costo_compra(self):
        costo = self.cleaned_data.get('costo_compra')
        if costo is None or costo < 0:
            raise forms.ValidationError('Ingrese un costo v?lido.')
        return costo

    def clean(self):
        cleaned = super().clean()
        user = self._user
        desde = cleaned.get('descuento_desde')
        hasta = cleaned.get('descuento_hasta')
        if desde and hasta and hasta < desde:
            self.add_error('descuento_hasta', 'La fecha fin no puede ser menor que la fecha inicio.')
        contenido = cleaned.get('contenido')
        unidad = cleaned.get('unidad_contenido')
        tipo = cleaned.get('tipo')
        fecha_vencimiento = cleaned.get('fecha_vencimiento')
        lote = cleaned.get('lote')
        if user and not (user.groups.filter(name='ADMIN').exists() or user.is_superuser):
            if not user.has_perm('inventario.change_producto_stock'):
                cleaned['stock_inicial'] = self.instance.stock_inicial
                cleaned['stock_minimo'] = self.instance.stock_minimo
            if not user.has_perm('inventario.change_producto_precio'):
                cleaned['precio'] = self.instance.precio
            if not user.has_perm('inventario.change_producto_costo'):
                cleaned['costo_compra'] = self.instance.costo_compra
            if not user.has_perm('inventario.change_producto_lote'):
                cleaned['lote'] = self.instance.lote
                cleaned['fecha_vencimiento'] = self.instance.fecha_vencimiento
            if self.instance and self.instance.pk:
                cleaned['precio'] = self.instance.precio
                cleaned['costo_compra'] = self.instance.costo_compra
        if contenido and not unidad:
            self.add_error('unidad_contenido', 'Seleccione la unidad del contenido.')
        if unidad and not contenido:
            self.add_error('contenido', 'Ingrese el contenido por unidad.')
        if tipo == Producto.TIPO_MEDICAMENTO:
            if not fecha_vencimiento:
                self.add_error('fecha_vencimiento', 'La fecha de vencimiento es obligatoria para medicamentos.')
            if not lote:
                self.add_error('lote', 'El lote es obligatorio para medicamentos.')
        if tipo == Producto.TIPO_SERVICIO:
            cleaned['stock_inicial'] = 0
            cleaned['stock_minimo'] = 0
            cleaned['lote'] = ''
            cleaned['fecha_vencimiento'] = None
            cleaned['codigo'] = ''
            cleaned['proveedor'] = ''
            cleaned['presentacion'] = ''
            cleaned['contenido'] = None
            cleaned['unidad_contenido'] = ''
            cleaned['costo_compra'] = 0
        return cleaned


class ProductoDescuentoCreateForm(forms.Form):
    APLICA_PRODUCTO = 'PRODUCTO'
    APLICA_TIPO = 'TIPO'
    APLICA_CHOICES = [
        (APLICA_PRODUCTO, 'Producto o servicio'),
        (APLICA_TIPO, 'Tipo (medicamento, accesorio o servicio)'),
    ]

    aplica_a = forms.ChoiceField(
        choices=APLICA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Aplicar a',
        initial=APLICA_PRODUCTO,
    )
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all().order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Producto o servicio',
        required=False,
    )
    tipo = forms.ChoiceField(
        choices=Producto.TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de producto',
        required=False,
    )
    descuento_pct = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Descuento (%)',
    )
    descuento_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Desde',
    )
    descuento_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Hasta',
    )

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.fields.get('descuento_desde'):
            self.fields['descuento_desde'].input_formats = ['%Y-%m-%d']
        if self.fields.get('descuento_hasta'):
            self.fields['descuento_hasta'].input_formats = ['%Y-%m-%d']

    def clean(self):
        cleaned = super().clean()
        aplica = cleaned.get('aplica_a') or self.initial.get('aplica_a')
        if aplica == self.APLICA_PRODUCTO:
            if not cleaned.get('producto'):
                initial_producto = self.initial.get('producto')
                if initial_producto:
                    cleaned['producto'] = initial_producto
                else:
                    self.add_error('producto', 'Selecciona un producto.')
            cleaned['tipo'] = ''
        elif aplica == self.APLICA_TIPO:
            if not cleaned.get('tipo'):
                initial_tipo = self.initial.get('tipo')
                if initial_tipo:
                    cleaned['tipo'] = initial_tipo
                else:
                    self.add_error('tipo', 'Selecciona un tipo.')
            cleaned['producto'] = None
        desde = cleaned.get('descuento_desde')
        hasta = cleaned.get('descuento_hasta')
        if desde and hasta and hasta < desde:
            self.add_error('descuento_hasta', 'La fecha fin no puede ser menor que la fecha inicio.')
        return cleaned

    def save(self):
        aplica = self.cleaned_data.get('aplica_a')
        if aplica == self.APLICA_TIPO:
            tipo = self.cleaned_data['tipo']
            descuento, _ = TipoDescuento.objects.update_or_create(
                tipo=tipo,
                defaults={
                    'descuento_pct': self.cleaned_data['descuento_pct'],
                    'descuento_desde': self.cleaned_data.get('descuento_desde'),
                    'descuento_hasta': self.cleaned_data.get('descuento_hasta'),
                }
            )
            return descuento
        producto = self.cleaned_data['producto']
        producto.descuento_pct = self.cleaned_data['descuento_pct']
        producto.descuento_desde = self.cleaned_data.get('descuento_desde')
        producto.descuento_hasta = self.cleaned_data.get('descuento_hasta')
        producto.save(update_fields=['descuento_pct', 'descuento_desde', 'descuento_hasta'])
        return producto

class RecordatorioForm(forms.ModelForm):
    class Meta:
        model = Recordatorio
        fields = ['titulo', 'tipo', 'fecha', 'proveedor', 'producto', 'cantidad', 'notas', 'estado']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        producto = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')

        if tipo != Recordatorio.TIPO_ENTRADA:
            # For proveedor visits, ignore producto/cantidad
            cleaned['producto'] = None
            cleaned['cantidad'] = None
            return cleaned

        if cantidad and not producto:
            self.add_error('producto', 'Selecciona un producto si agregas cantidad.')
        return cleaned


class StockAdjustmentRequestForm(forms.ModelForm):
    class Meta:
        model = StockAdjustmentRequest
        fields = ['producto', 'cantidad', 'lote', 'fecha_vencimiento', 'motivo']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        producto = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')
        lote = cleaned.get('lote')
        fecha_vencimiento = cleaned.get('fecha_vencimiento')
        motivo = (cleaned.get('motivo') or '').strip()
        if cantidad in (None, 0):
            self.add_error('cantidad', 'La cantidad no puede ser 0.')
        if producto and producto.tipo == Producto.TIPO_SERVICIO:
            self.add_error('producto', 'No se pueden ajustar servicios.')
        if not motivo:
            self.add_error('motivo', 'El motivo es obligatorio.')
        if producto and producto.tipo == Producto.TIPO_MEDICAMENTO:
            if not lote:
                self.add_error('lote', 'El lote es obligatorio para medicamentos.')
            if not fecha_vencimiento:
                self.add_error('fecha_vencimiento', 'La fecha de vencimiento es obligatoria para medicamentos.')
        return cleaned
