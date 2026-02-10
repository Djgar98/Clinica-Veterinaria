from django import forms
from django.contrib.auth import get_user_model
from .models import Consulta, Mascota, Cita, SolicitudCita, SolicitudReprogramacion, RecetaItem
from inventario.models import ProductoLote
from usuarios.models import Staff


class ConsultaForm(forms.ModelForm):
    cerrar_consulta = forms.BooleanField(required=False, initial=True, label='Cerrar consulta')
    seguimiento_fecha = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}))

    class Meta:
        model = Consulta
        fields = ['diagnostico', 'descripcion']
        widgets = {
            'diagnostico': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['seguimiento_fecha'].label = 'Crear cita de seguimiento'


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['mascota', 'fecha', 'veterinario', 'estado', 'notas']
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'veterinario': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['veterinario'].queryset = Staff.objects.filter(
            is_active=True,
            cargo__in=['VETERINARIO', 'ADMIN']
        ).order_by('nombre_completo')
        estado_field = self.fields.get('estado')
        if estado_field:
            estado_field.choices = [
                (value, label)
                for value, label in estado_field.choices
                if value != Cita.ESTADO_ATENDIDA
            ]
        # Ensure datetime-local displays existing value on edit
        fecha_field = self.fields.get('fecha')
        if fecha_field:
            fecha_field.input_formats = ['%Y-%m-%dT%H:%M']
            if self.instance and self.instance.pk and self.instance.fecha:
                fecha_field.initial = self.instance.fecha.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned = super().clean()
        veterinario = cleaned.get('veterinario')
        fecha = cleaned.get('fecha')
        if veterinario and fecha:
            qs = Cita.objects.filter(veterinario=veterinario, fecha=fecha)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('El veterinario ya tiene una cita en esa fecha y hora.')
        return cleaned


class SolicitudCitaForm(forms.ModelForm):
    class Meta:
        model = SolicitudCita
        fields = ['mascota', 'fecha_preferida', 'motivo']
        widgets = {
            'mascota': forms.Select(attrs={'class': 'form-select'}),
            'fecha_preferida': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SolicitudReprogramacionForm(forms.ModelForm):
    class Meta:
        model = SolicitudReprogramacion
        fields = ['nueva_fecha', 'descripcion']
        widgets = {
            'nueva_fecha': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RecetaItemForm(forms.ModelForm):
    class Meta:
        model = RecetaItem
        fields = ['producto', 'cantidad', 'lote']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
        }


from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Receta


class BaseRecetaItemFormSet(BaseInlineFormSet):
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
            if producto and cantidad:
                has_item = True
            elif producto or cantidad:
                raise forms.ValidationError('Completa producto y cantidad en cada ítem.')
        if not has_item:
            return


RecetaItemFormSet = inlineformset_factory(
    Receta,
    RecetaItem,
    form=RecetaItemForm,
    formset=BaseRecetaItemFormSet,
    extra=1,
    can_delete=True,
)


class ReservaLoteForm(forms.Form):
    lote = forms.ModelChoiceField(queryset=ProductoLote.objects.none(), label='Lote')
    cantidad = forms.IntegerField(min_value=1, label='Cantidad')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lote'].queryset = ProductoLote.objects.select_related('producto').filter(cantidad__gt=0).order_by('fecha_vencimiento')
        self.fields['lote'].widget.attrs.update({'class': 'form-select'})
        self.fields['cantidad'].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned = super().clean()
        lote = cleaned.get('lote')
        qty = cleaned.get('cantidad')
        if lote and qty and qty > lote.cantidad:
            self.add_error('cantidad', 'La cantidad a reservar excede el stock del lote.')
        return cleaned


class MascotaForm(forms.ModelForm):
    class Meta:
        model = Mascota
        fields = [
            'nombre', 'especie', 'raza', 'fecha_nacimiento', 'sexo',
            'color', 'tamanio', 'peso_kg', 'esterilizado', 'microchip',
            'alergias', 'vacunas', 'senas_particulares', 'notas', 'owner',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'especie': forms.TextInput(attrs={'class': 'form-control'}),
            'raza': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'tamanio': forms.Select(attrs={'class': 'form-select'}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'esterilizado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'microchip': forms.TextInput(attrs={'class': 'form-control'}),
            'alergias': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'vacunas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'senas_particulares': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner_field = self.fields.get('owner')
        if owner_field:
            owner_field.queryset = get_user_model().objects.filter(
                is_active=True,
                groups__name='DUENO'
            ).distinct().order_by('first_name', 'last_name', 'username')
            owner_field.label_from_instance = lambda obj: obj.get_full_name() or obj.username

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha and self.instance and self.instance.pk:
            return self.instance.fecha_nacimiento
        return fecha
