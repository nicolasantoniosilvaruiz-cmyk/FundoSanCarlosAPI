from decimal import Decimal
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Estanque


class IngresoForm(AuthenticationForm):
    username = forms.CharField(label='Usuario', widget=forms.TextInput(attrs={'autocomplete': 'username', 'placeholder': 'Tu nombre de usuario', 'autofocus': True}))
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Tu contraseña'}))


class UmbralForm(forms.ModelForm):
    class Meta:
        model = Estanque
        fields = ['umbral_pct']
        labels = {'umbral_pct': 'Nivel mínimo de agua (%)'}
        widgets = {'umbral_pct': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01', 'inputmode': 'decimal'})}


class SimulacionForm(forms.Form):
    estanque = forms.ModelChoiceField(queryset=Estanque.objects.filter(tipo='agua'), label='Estanque')
    porcentaje = forms.DecimalField(label='Nivel del estanque (%)', min_value=0, max_value=100, max_digits=5, decimal_places=2, widget=forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01', 'inputmode': 'decimal'}))


class CapacidadVisualForm(forms.Form):
    capacidad_visual_litros = forms.DecimalField(
        label='Capacidad representada del agua (L)', min_value=Decimal('0.001'),
        max_digits=12, decimal_places=3,
        widget=forms.NumberInput(attrs={'min': '0.001', 'step': '0.001', 'inputmode': 'decimal'}))
