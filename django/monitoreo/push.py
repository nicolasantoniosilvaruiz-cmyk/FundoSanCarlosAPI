import base64
import json
import logging
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey, SECP256R1
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.conf import settings
from django.utils import timezone
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from .models import Alerta, SuscripcionPush

logger = logging.getLogger(__name__)


def clave_publica():
    if not settings.PUSH_KEY_FILE.is_file() or not settings.PUSH_CONTACT:
        return ''
    key = Vapid.from_file(str(settings.PUSH_KEY_FILE)).public_key
    raw = key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def endpoint_permitido(endpoint):
    if not isinstance(endpoint, str) or len(endpoint) > 2048 or not endpoint.isascii():
        return False
    try:
        url = urlsplit(endpoint)
        host = url.hostname or ''
        return (
            url.scheme == 'https' and url.netloc == host and url.path.startswith('/')
            and not url.fragment and not any(c.isspace() or ord(c) < 32 for c in endpoint)
            and (host in {'fcm.googleapis.com', 'updates.push.services.mozilla.com', 'push.services.mozilla.com', 'web.push.apple.com'}
                 or host.endswith('.push.apple.com')
                 or host.endswith('.notify.windows.com'))
        )
    except ValueError:
        return False


def validar_claves(keys):
    if not isinstance(keys, dict):
        return False
    try:
        auth, public = keys['auth'], keys['p256dh']
        if not isinstance(auth, str) or not isinstance(public, str) or len(auth) > 24 or len(public) > 90:
            return False
        def decode(value):
            return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)
        point = decode(public)
        return len(decode(auth)) == 16 and len(point) == 65 and bool(
            EllipticCurvePublicKey.from_encoded_point(SECP256R1(), point)
        )
    except (KeyError, ValueError, TypeError):
        return False


class SinRedirecciones(requests.Session):
    def request(self, *args, **kwargs):
        kwargs['allow_redirects'] = False
        return super().request(*args, **kwargs)


def enviar(suscripcion, mensaje):
    # Nunca hacer POST a una URL arbitraria aportada por el navegador.
    if not endpoint_permitido(suscripcion.endpoint):
        return False
    try:
        with SinRedirecciones() as session:
            response = webpush(
                subscription_info={'endpoint': suscripcion.endpoint, 'keys': {
                    'p256dh': suscripcion.p256dh, 'auth': suscripcion.auth}},
                data=json.dumps(mensaje, ensure_ascii=False),
                vapid_private_key=Vapid.from_file(str(settings.PUSH_KEY_FILE)),
                vapid_claims={'sub': settings.PUSH_CONTACT},
                ttl=180, timeout=4, requests_session=session,
            )
        return 200 <= response.status_code < 300
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            suscripcion.delete()
        logger.warning('Servicio Web Push rechazó un aviso (HTTP %s).', status)
    except (requests.RequestException, ValueError, OSError):
        logger.warning('No se pudo conectar con el servicio Web Push o preparar el aviso.')
    return False


def notificar_alerta(alerta_id):
    if not clave_publica():
        return
    alerta = Alerta.objects.select_related('medicion', 'estanque').get(pk=alerta_id)
    if alerta.resuelta is not None:
        return
    # Una emisión por alerta: si el proveedor no responde, no reenviar a ciegas.
    if not Alerta.objects.filter(pk=alerta_id, push_evaluada_en__isnull=True).update(push_evaluada_en=timezone.now()):
        return
    mensaje = {
        'title': 'Nivel bajo de agua',
        'body': f'Queda {alerta.medicion.porcentaje:.1f} % de agua. Umbral: {alerta.umbral_aplicado:g} %.',
        'url': '/alertas/', 'tag': f'agua-{alerta.pk}',
    }
    suscripciones = SuscripcionPush.objects.filter(usuario__is_active=True, usuario__rol='administrador', origen=settings.PUBLIC_ORIGIN)
    aceptadas = sum(enviar(s, mensaje) for s in suscripciones)
    Alerta.objects.filter(pk=alerta_id).update(push_aceptadas=aceptadas)
