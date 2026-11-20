import hashlib
import secrets
from functools import wraps

from django import forms
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .api_agua import leer_json
from .fcm import configurado
from .models import Alerta, Estanque, Medicion, SesionMovil
from .services import configurar_umbral, estado_estanque, registrar_simulacion


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def error(message, status):
    return JsonResponse({'error': message}, status=status)


def autenticado(view):
    @wraps(view)
    def wrapped(request):
        scheme, _, token = request.headers.get('Authorization', '').partition(' ')
        if scheme != 'Bearer' or len(token) != 43 or not token.isascii():
            return error('Inicia sesión para continuar.', 401)
        session = SesionMovil.objects.select_related('usuario').filter(
            token_hash=digest(token), expira_en__gt=timezone.now(), usuario__is_active=True,
        ).first()
        if session is None:
            return error('La sesión expiró. Vuelve a ingresar.', 401)
        # Cambiar la contraseña también invalida las sesiones Android existentes.
        if session.huella_usuario != session.usuario.get_session_auth_hash():
            session.delete()
            return error('La sesión expiró. Vuelve a ingresar.', 401)
        request.sesion_movil = session
        request.usuario_movil = session.usuario
        return view(request)
    return never_cache(wrapped)


def solo_admin(view):
    @wraps(view)
    def wrapped(request):
        if not request.usuario_movil.es_administrador:
            return error('Esta función es para el administrador.', 403)
        return view(request)
    return wrapped


def json_body(request):
    try:
        return leer_json(request)
    except ValueError:
        return None


@csrf_exempt  # API de Android: credenciales en JSON; no usa cookies.
@never_cache
@require_POST
def ingresar(request):
    data = json_body(request)
    if not data:
        return error('Solicitud inválida.', 400)
    cuenta, password = data.get('usuario'), data.get('contrasena')
    if not isinstance(cuenta, str) or not 1 <= len(cuenta.strip()) <= 150 or not isinstance(password, str) or not 1 <= len(password) <= 256:
        return error('Ingresa usuario y contraseña.', 400)
    cuenta = cuenta.strip()
    rate_key = 'movil:login:' + digest(cuenta.casefold())
    cache.add(rate_key, 0, timeout=60)
    try:
        attempts = cache.incr(rate_key)
    except ValueError:
        cache.set(rate_key, 1, timeout=60)
        attempts = 1
    if attempts > 10:
        return error('Demasiados intentos. Espera un minuto.', 429)
    user = authenticate(request, username=cuenta, password=password)
    if user is None:
        return error('Usuario o contraseña incorrectos.', 401)
    cache.delete(rate_key)
    SesionMovil.objects.filter(usuario=user, expira_en__lte=timezone.now()).delete()
    token = secrets.token_urlsafe(32)
    SesionMovil.objects.create(usuario=user, token_hash=digest(token),
                               huella_usuario=user.get_session_auth_hash(),
                               expira_en=timezone.now() + timezone.timedelta(days=14))
    return JsonResponse({'token': token, 'usuario': user.username,
                         'nombre': user.first_name or user.username, 'rol': user.rol})


@csrf_exempt
@require_POST
@autenticado
def salir(request):
    request.sesion_movil.delete()
    return JsonResponse({'ok': True})


@require_GET
@autenticado
def panel(request):
    user = request.usuario_movil
    estanques = [estado_estanque(e) for e in Estanque.objects.all()]
    if not user.es_administrador:
        for estanque in estanques:
            estanque.pop('umbral', None)
    historial = []
    lecturas = []
    if user.es_administrador:
        for a in Alerta.objects.select_related('medicion', 'estanque')[:20]:
            historial.append({'id': a.pk, 'fecha': a.creada.isoformat(), 'resuelta': a.resuelta is not None,
                               'litros': float(a.medicion.volumen_litros), 'umbral': float(a.umbral_aplicado),
                               'avisos_android': a.fcm_aceptadas})
        for m in Medicion.objects.select_related('estanque')[:12]:
            lecturas.append({'estanque': m.estanque.nombre, 'tipo': m.estanque.tipo,
                             'fecha': m.fecha_lectura.isoformat(), 'litros': float(m.volumen_litros),
                             'simulada': m.simulada})
    return JsonResponse({'usuario': user.username, 'nombre': user.first_name or user.username,
                         'rol': user.rol, 'estanques': estanques, 'alertas': historial, 'lecturas': lecturas,
                         'notificaciones_disponibles': user.es_administrador and configurado(),
                         'notificaciones_vinculadas': bool(request.sesion_movil.fcm_token)})


class PorcentajeForm(forms.Form):
    porcentaje = forms.DecimalField(min_value=0, max_value=100, max_digits=5, decimal_places=2)


@csrf_exempt
@require_POST
@autenticado
@solo_admin
def umbral(request):
    form = PorcentajeForm(json_body(request) or {})
    if not form.is_valid():
        return error('Ingresa un porcentaje entre 0 y 100, con hasta dos decimales.', 400)
    agua = Estanque.objects.filter(tipo='agua').first()
    if agua is None:
        return error('No hay un estanque de agua configurado.', 404)
    agua = configurar_umbral(agua.pk, form.cleaned_data['porcentaje'])
    return JsonResponse({'umbral': float(agua.umbral_pct)})


@csrf_exempt
@require_POST
@autenticado
@solo_admin
def lectura(request):
    data = json_body(request) or {}
    form = PorcentajeForm(data)
    if data.get('tipo') == 'petroleo':
        return error('Registra el combustible desde el módulo Petróleo.', 400)
    if not form.is_valid() or data.get('tipo') != 'agua':
        return error('Elige un estanque e ingresa un porcentaje entre 0 y 100.', 400)
    estanque = Estanque.objects.filter(tipo=data['tipo']).first()
    if estanque is None:
        return error('Estanque no configurado.', 404)
    medicion, alerta = registrar_simulacion(estanque.pk, form.cleaned_data['porcentaje'], request.usuario_movil)
    return JsonResponse({'id': str(medicion.pk), 'litros': float(medicion.volumen_litros),
                         'alerta_nueva': alerta}, status=201)


@csrf_exempt
@require_POST
@autenticado
@solo_admin
@transaction.atomic
def notificaciones(request):
    data = json_body(request)
    if data is None:
        return error('Solicitud inválida.', 400)
    session = request.sesion_movil
    if data.get('accion') == 'quitar':
        session.fcm_token = ''
        session.fcm_hash = None
    else:
        if not configurado():
            return error('Los avisos Android aún no están configurados en el servidor.', 503)
        token = data.get('token')
        if (not isinstance(token, str) or not 16 <= len(token) <= 2048 or not token.isascii()
                or not all(c.isalnum() or c in '-_:' for c in token)):
            return error('El registro del teléfono no es válido.', 400)
        token_hash = digest(token)
        SesionMovil.objects.filter(fcm_hash=token_hash).exclude(pk=session.pk).update(fcm_token='', fcm_hash=None)
        session.fcm_token = token
        session.fcm_hash = token_hash
    session.save(update_fields=['fcm_token', 'fcm_hash'])
    return JsonResponse({'ok': True})
