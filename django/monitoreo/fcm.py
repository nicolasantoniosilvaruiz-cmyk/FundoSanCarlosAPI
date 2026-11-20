import logging
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def configurado():
    return bool(settings.FCM_PROJECT_ID and settings.FCM_CREDENTIALS
                and Path(settings.FCM_CREDENTIALS).is_file())


def enviar_alerta_android(alerta_id):
    if not configurado():
        return
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    from requests import RequestException

    from .models import Alerta, SesionMovil

    alerta = Alerta.objects.select_related('medicion', 'estanque').filter(pk=alerta_id, resuelta__isnull=True).first()
    if alerta is None:
        return
    # Se reserva el envío al confirmar la alerta, evitando duplicados en reintentos.
    if not Alerta.objects.filter(pk=alerta.pk, fcm_evaluada_en__isnull=True).update(fcm_evaluada_en=timezone.now()):
        return
    sesiones = [s for s in SesionMovil.objects.select_related('usuario').filter(
        fcm_hash__isnull=False, expira_en__gt=timezone.now(), usuario__is_active=True, usuario__rol='administrador'
    ) if s.huella_usuario == s.usuario.get_session_auth_hash()]
    if not sesiones:
        return
    try:
        cred = service_account.Credentials.from_service_account_file(
            settings.FCM_CREDENTIALS, scopes=['https://www.googleapis.com/auth/firebase.messaging'])
    except (GoogleAuthError, OSError, ValueError):
        logger.warning('No se pudo cargar la credencial FCM del servidor.')
        return
    url = f'https://fcm.googleapis.com/v1/projects/{quote(settings.FCM_PROJECT_ID, safe="")}/messages:send'
    aceptadas = 0
    with AuthorizedSession(cred, refresh_timeout=6) as session:
        for item in sesiones:
            payload = {'message': {
                'token': item.fcm_token,
                'notification': {'title': 'Nivel bajo de agua',
                                 'body': f'Queda {alerta.medicion.porcentaje:.1f} % de agua. Umbral: {alerta.umbral_aplicado:g} %.'},
                'data': {'alerta_id': str(alerta.pk), 'pantalla': 'agua'},
                'android': {'priority': 'HIGH', 'ttl': '180s', 'notification': {
                    'channel_id': 'alertas_agua', 'tag': f'agua-{alerta.pk}', 'visibility': 'PUBLIC'}},
            }}
            try:
                response = session.post(url, json=payload, timeout=6, allow_redirects=False)
            except (GoogleAuthError, RequestException):
                logger.warning('FCM no respondió al enviar un aviso de agua.')
                continue
            if response.ok and response.status_code < 300:
                aceptadas += 1
            else:
                try:
                    details = response.json().get('error', {}).get('details', [])
                except ValueError:
                    details = []
                if any(d.get('errorCode') == 'UNREGISTERED' for d in details if isinstance(d, dict)):
                    SesionMovil.objects.filter(pk=item.pk, fcm_hash=item.fcm_hash).update(fcm_token='', fcm_hash=None)
                logger.warning('FCM rechazó un aviso de agua (HTTP %s).', response.status_code)
    Alerta.objects.filter(pk=alerta.pk).update(fcm_aceptadas=aceptadas)
