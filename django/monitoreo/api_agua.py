import hashlib
import json
import re
import uuid
from decimal import Decimal

from django import forms
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import DispositivoAgua, Estanque, Medicion
from .services import evaluar_alerta, ultima_medicion


def leer_json(request):
    if request.content_type != 'application/json' or len(request.body) > 8192:
        raise ValueError
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError
    return data


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class LecturaForm(forms.Form):
    id = forms.UUIDField()
    porcentaje = forms.DecimalField(min_value=0, max_value=100, max_digits=5, decimal_places=2)
    tomada_en = forms.DateTimeField()

    def clean_tomada_en(self):
        dato = self.cleaned_data['tomada_en']
        if not re.search(r'(Z|[+-]\d\d:\d\d)$', str(self.data.get('tomada_en'))):
            raise forms.ValidationError('Usa una fecha ISO 8601 con zona horaria.')
        if dato > timezone.now() + timezone.timedelta(minutes=2):
            raise forms.ValidationError('La fecha de lectura está en el futuro.')
        return dato


@csrf_exempt  # Solo token de dispositivo; esta vista no autoriza por cookies.
@require_POST
@never_cache
def recibir_agua(request):
    codigo = request.headers.get('X-Dispositivo', '')
    auth = request.headers.get('Authorization', '')
    if not re.fullmatch(r'[a-z0-9-]{1,50}', codigo) or not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}', auth):
        return JsonResponse({'error': 'Credencial de dispositivo inválida.'}, status=401)
    try:
        data = leer_json(request)
    except ValueError:
        return JsonResponse({'error': 'Envía un objeto JSON de hasta 8 KB.'}, status=400)
    with transaction.atomic():
        disp = DispositivoAgua.objects.select_for_update().select_related('estanque').filter(
            codigo=codigo, activo=True, estanque__tipo='agua').first()
        if not disp or not constant_time_compare(disp.token_hash, hash_token(auth[7:])):
            return JsonResponse({'error': 'Credencial de dispositivo inválida.'}, status=401)
        if not isinstance(data.get('id'), str) or not isinstance(data.get('tomada_en'), str):
            return JsonResponse({'error': 'El UUID y tomada_en deben ser cadenas.'}, status=400)
        form = LecturaForm(data)
        if not form.is_valid():
            return JsonResponse({'error': 'Lectura inválida.', 'campos': form.errors.get_json_data()}, status=400)
        lectura = form.cleaned_data
        estanque = Estanque.objects.select_for_update().get(pk=disp.estanque_id)
        volumen = (estanque.capacidad_litros * lectura['porcentaje'] / 100).quantize(Decimal('0.001'))
        anterior = ultima_medicion(estanque)
        medicion, nueva = Medicion.objects.get_or_create(pk=lectura['id'], defaults={
            'estanque': estanque, 'dispositivo': disp, 'volumen_litros': volumen,
            'tomada_en': lectura['tomada_en'], 'simulada': disp.simulador,
        })
        if not nueva and (
            medicion.dispositivo_id != disp.pk or medicion.tomada_en != lectura['tomada_en']
            or medicion.volumen_litros != volumen
        ):
            return JsonResponse({'error': 'Ese UUID ya pertenece a otra lectura.'}, status=409)
        alerta = False
        if nueva and (anterior is None or medicion.tomada_en >= anterior.fecha_lectura):
            alerta = evaluar_alerta(estanque, medicion)
        return JsonResponse({'id': str(medicion.pk), 'duplicada': not nueva, 'alerta_nueva': alerta},
                            status=201 if nueva else 200)
