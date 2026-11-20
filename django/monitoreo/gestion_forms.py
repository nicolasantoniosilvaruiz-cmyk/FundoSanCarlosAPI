import re
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario


class RutMixin:
    def clean_rut(self):
        value = (self.cleaned_data.get('rut') or '').strip().upper().replace('.', '').replace(' ', '')
        if not value:
            return None
        if not re.fullmatch(r'[0-9]{7,8}-[0-9K]', value):
            raise forms.ValidationError('Ingresa un RUT con guion, por ejemplo 12345678-5.')
        cuerpo, digito = value.split('-')
        total = sum(int(numero) * (2 + i % 6) for i, numero in enumerate(reversed(cuerpo)))
        resultado = 11 - total % 11
        esperado = '0' if resultado == 11 else 'K' if resultado == 10 else str(resultado)
        if digito != esperado:
            raise forms.ValidationError('El digito verificador del RUT no coincide.')
        return f'{int(cuerpo)}-{digito}'


class EmpleadoNuevoForm(RutMixin, UserCreationForm):
    rut = forms.CharField(label='RUT', max_length=12)

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'rut', 'email', 'rol']
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Correo'}


class EmpleadoEditarForm(RutMixin, forms.ModelForm):
    rut = forms.CharField(label='RUT', max_length=12, required=False)
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'rut', 'email', 'rol', 'is_active']
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Correo', 'is_active': 'Acceso activo'}


class MovimientoForm(forms.Form):
    solicitud = forms.UUIDField(widget=forms.HiddenInput)
    revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    antes = forms.DecimalField(label='Cantidad actual (L)', min_value=0, max_value=1000, max_digits=7, decimal_places=3)
    cantidad = forms.DecimalField(label='Cantidad a retirar (L)', min_value=Decimal('0.001'), max_value=1000, max_digits=7, decimal_places=3)
    despues = forms.DecimalField(label='Cantidad que quedó (L)', min_value=0, max_value=1000, max_digits=7, decimal_places=3)
    tipo = forms.ChoiceField(choices=[('retiro', 'Retiro'), ('recarga', 'Recarga')], widget=forms.HiddenInput)
