from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Staff, OwnerProfile
from .roles import (
    ROLE_CHOICES,
    ROLE_DUENO,
    set_user_roles,
    get_user_roles,
)


class UserCreateForm(UserCreationForm):
    documento_validator = RegexValidator(
        regex=r'^\d{3}-\d{6}-\d{4}[A-Za-z]$',
        message='El documento debe tener el formato 000-000000-0000X.',
    )
    roles = forms.MultipleChoiceField(choices=ROLE_CHOICES, label='Roles', widget=forms.CheckboxSelectMultiple)
    is_active = forms.BooleanField(required=False, initial=True, label='Usuario activo')
    telefono = forms.CharField(required=False, label='Teléfono')
    direccion = forms.CharField(required=False, label='Dirección')
    documento = forms.CharField(required=False, label='Documento', validators=[documento_validator], help_text='Formato: 000-000000-0000X')
    fecha_nacimiento = forms.DateField(required=False, label='Fecha de nacimiento', widget=forms.DateInput(attrs={'type': 'date'}))
    genero = forms.ChoiceField(
        required=False,
        label='Género',
        choices=[('', 'Seleccione'), ('F', 'Femenino'), ('M', 'Masculino'), ('O', 'Otro')],
    )
    owner_contacto = forms.CharField(required=False, label='Contacto de emergencia')
    owner_notas = forms.CharField(required=False, label='Notas (dueño)', widget=forms.Textarea(attrs={'rows': 2}))

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']:
            if name in self.fields:
                self.fields[name].widget.attrs.update({'class': 'form-control'})
        self.fields['roles'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        for name in [
            'telefono', 'direccion', 'documento', 'fecha_nacimiento', 'genero',
            'owner_contacto', 'owner_notas',
        ]:
            if name in self.fields:
                if isinstance(self.fields[name].widget, forms.Select):
                    self.fields[name].widget.attrs.update({'class': 'form-select'})
                else:
                    self.fields[name].widget.attrs.update({'class': 'form-control'})
        if 'documento' in self.fields:
            self.fields['documento'].widget.attrs.update({'data-doc-format': 'true'})

    def clean_documento(self):
        value = (self.cleaned_data.get('documento') or '').strip().upper()
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_active = bool(self.cleaned_data.get('is_active'))
        if commit:
            user.save()
            roles = self.cleaned_data.get('roles') or [ROLE_DUENO]
            set_user_roles(user, roles=roles)
            OwnerProfile.objects.update_or_create(
                user=user,
                defaults={
                    'telefono': self.cleaned_data.get('telefono', ''),
                    'direccion': self.cleaned_data.get('direccion', ''),
                    'documento': self.cleaned_data.get('documento', ''),
                    'contacto_emergencia': self.cleaned_data.get('owner_contacto', ''),
                    'fecha_nacimiento': self.cleaned_data.get('fecha_nacimiento'),
                    'genero': self.cleaned_data.get('genero', ''),
                    'notas': self.cleaned_data.get('owner_notas', ''),
                }
            )
            staff = Staff.objects.filter(user=user).first()
            if staff:
                staff.telefono = self.cleaned_data.get('telefono', '')
                staff.documento = self.cleaned_data.get('documento', '')
                staff.direccion = self.cleaned_data.get('direccion', '')
                staff.fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
                staff.genero = self.cleaned_data.get('genero', '')
                staff.save(update_fields=['telefono', 'documento', 'direccion', 'fecha_nacimiento', 'genero'])
        return user


class UserUpdateForm(UserChangeForm):
    documento_validator = RegexValidator(
        regex=r'^\d{3}-\d{6}-\d{4}[A-Za-z]$',
        message='El documento debe tener el formato 000-000000-0000X.',
    )
    roles = forms.MultipleChoiceField(choices=ROLE_CHOICES, label='Roles', widget=forms.CheckboxSelectMultiple)
    password = None
    is_active = forms.BooleanField(required=False, label='Usuario activo')
    telefono = forms.CharField(required=False, label='Teléfono')
    direccion = forms.CharField(required=False, label='Dirección')
    documento = forms.CharField(required=False, label='Documento', validators=[documento_validator], help_text='Formato: 000-000000-0000X')
    fecha_nacimiento = forms.DateField(required=False, label='Fecha de nacimiento', widget=forms.DateInput(attrs={'type': 'date'}))
    genero = forms.ChoiceField(
        required=False,
        label='Género',
        choices=[('', 'Seleccione'), ('F', 'Femenino'), ('M', 'Masculino'), ('O', 'Otro')],
    )
    owner_contacto = forms.CharField(required=False, label='Contacto de emergencia')
    owner_notas = forms.CharField(required=False, label='Notas (dueño)', widget=forms.Textarea(attrs={'rows': 2}))

    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password', None)
        for name in ['username', 'email', 'first_name', 'last_name']:
            if name in self.fields:
                self.fields[name].widget.attrs.update({'class': 'form-control'})
        self.fields['roles'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        for name in [
            'telefono', 'direccion', 'documento', 'fecha_nacimiento', 'genero',
            'owner_contacto', 'owner_notas',
        ]:
            if name in self.fields:
                if isinstance(self.fields[name].widget, forms.Select):
                    self.fields[name].widget.attrs.update({'class': 'form-select'})
                else:
                    self.fields[name].widget.attrs.update({'class': 'form-control'})
        if 'documento' in self.fields:
            self.fields['documento'].widget.attrs.update({'data-doc-format': 'true'})

        staff = Staff.objects.filter(user=self.instance).first()
        owner_profile = OwnerProfile.objects.filter(user=self.instance).first()
        def pick(owner_val, staff_val):
            return owner_val if owner_val not in (None, '') else staff_val
        def fmt_date(val):
            return val.isoformat() if hasattr(val, 'isoformat') else val
        if owner_profile or staff:
            self.fields['telefono'].initial = pick(
                owner_profile.telefono if owner_profile else None,
                staff.telefono if staff else None,
            )
            self.fields['direccion'].initial = pick(
                owner_profile.direccion if owner_profile else None,
                staff.direccion if staff else None,
            )
            self.fields['documento'].initial = pick(
                owner_profile.documento if owner_profile else None,
                staff.documento if staff else None,
            )
            self.fields['fecha_nacimiento'].initial = fmt_date(pick(
                owner_profile.fecha_nacimiento if owner_profile else None,
                staff.fecha_nacimiento if staff else None,
            ))
            self.fields['genero'].initial = pick(
                owner_profile.genero if owner_profile else None,
                staff.genero if staff else None,
            )
        if owner_profile:
            self.fields['owner_contacto'].initial = owner_profile.contacto_emergencia
            self.fields['owner_notas'].initial = owner_profile.notas

        self.fields['is_active'].initial = self.instance.is_active
        self.fields['roles'].initial = list(get_user_roles(self.instance)) or [ROLE_DUENO]

    def clean_documento(self):
        value = (self.cleaned_data.get('documento') or '').strip().upper()
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.is_active = bool(self.cleaned_data.get('is_active'))
            user.save()
            roles = self.cleaned_data.get('roles') or [ROLE_DUENO]
            set_user_roles(user, roles=roles)
            OwnerProfile.objects.update_or_create(
                user=user,
                defaults={
                    'telefono': self.cleaned_data.get('telefono', ''),
                    'direccion': self.cleaned_data.get('direccion', ''),
                    'documento': self.cleaned_data.get('documento', ''),
                    'contacto_emergencia': self.cleaned_data.get('owner_contacto', ''),
                    'fecha_nacimiento': self.cleaned_data.get('fecha_nacimiento'),
                    'genero': self.cleaned_data.get('genero', ''),
                    'notas': self.cleaned_data.get('owner_notas', ''),
                }
            )
            staff = Staff.objects.filter(user=user).first()
            if staff:
                staff.telefono = self.cleaned_data.get('telefono', '')
                staff.documento = self.cleaned_data.get('documento', '')
                staff.direccion = self.cleaned_data.get('direccion', '')
                staff.fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
                staff.genero = self.cleaned_data.get('genero', '')
                staff.save(update_fields=['telefono', 'documento', 'direccion', 'fecha_nacimiento', 'genero'])
        return user
