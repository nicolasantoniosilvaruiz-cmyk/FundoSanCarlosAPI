import hashlib

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .api_agua import leer_json
from .models import SuscripcionPush
from .push import clave_publica, endpoint_permitido, validar_claves
from .views import administrador_required


@require_GET
@never_cache
def service_worker(request):
    return render(request, 'monitoreo/service-worker.js', content_type='application/javascript')


@require_GET
def manifest(request):
    return JsonResponse({
        'id': '/', 'start_url': '/agua/', 'name': 'Fundo San Carlos',
        'short_name': 'San Carlos', 'display': 'standalone',
        'background_color': '#f4f6f2', 'theme_color': '#173d32',
        'icons': [{'src': '/static/img/san-carlos.png', 'sizes': '192x192', 'type': 'image/png'}],
    }, content_type='application/manifest+json')


@never_cache
@administrador_required
@require_POST
def suscripcion(request):
    if not clave_publica():
        return JsonResponse({'error': 'Web Push aún no está configurado en el servidor.'}, status=503)
    try:
        data = leer_json(request)
    except ValueError:
        return JsonResponse({'error': 'Suscripción inválida.'}, status=400)
    endpoint = data.get('endpoint')
    if not endpoint_permitido(endpoint):
        return JsonResponse({'error': 'Servicio de notificaciones no compatible.'}, status=400)
    digest = hashlib.sha256(endpoint.encode()).hexdigest()
    origen = request.build_absolute_uri('/').rstrip('/')
    propias = SuscripcionPush.objects.filter(usuario=request.user, origen=origen)
    accion = data.get('accion', 'guardar')
    if accion == 'quitar':
        propias.filter(endpoint_hash=digest).delete()
        return JsonResponse({'ok': True})
    keys = data.get('keys')
    if accion != 'guardar' or not validar_claves(keys):
        return JsonResponse({'error': 'Las claves de la suscripción no son válidas.'}, status=400)
    # Un navegador puede cambiar de cuenta. El endpoint queda asignado a su último administrador.
    if propias.count() >= 5 and not propias.filter(endpoint_hash=digest).exists():
        return JsonResponse({'error': 'Ya hay cinco dispositivos registrados en esta cuenta.'}, status=409)
    SuscripcionPush.objects.update_or_create(endpoint_hash=digest, defaults={
        'usuario': request.user, 'origen': origen, 'endpoint': endpoint, 'p256dh': keys['p256dh'], 'auth': keys['auth'],
    })
    return JsonResponse({'ok': True})
