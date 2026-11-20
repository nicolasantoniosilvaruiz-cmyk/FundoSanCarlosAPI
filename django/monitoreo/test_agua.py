import base64
import json
import uuid
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ec import generate_private_key, SECP256R1
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.test import Client, TestCase, override_settings
from py_vapid import Vapid
from django.urls import reverse
from django.utils import timezone

from .api_agua import hash_token
from .models import Alerta, DispositivoAgua, Estanque, Medicion, SuscripcionPush, Usuario


class AguaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.agua = Estanque.objects.create(nombre='Agua', tipo='agua', capacidad_litros=30000, umbral_pct=30)
        cls.token = 'x' * 43
        cls.disp = DispositivoAgua.objects.create(codigo='agua-simulador', estanque=cls.agua, token_hash=hash_token(cls.token))
        cls.encargado = Usuario.objects.create_user(username='encargado', rol='administrador')
        cls.trabajador = Usuario.objects.create_user(username='operario', rol='trabajador')

    def evento(self, pct, fecha=None):
        return {'id': str(uuid.uuid4()), 'porcentaje': str(pct), 'tomada_en': (fecha or timezone.now()).isoformat()}

    def enviar(self, dato, token=None):
        return self.client.post(reverse('recibir_agua'), dato, content_type='application/json',
                                headers={'Authorization': 'Bearer ' + (token or self.token), 'X-Dispositivo': self.disp.codigo})

    def test_token_obligatorio_incluso_con_sesion_admin(self):
        self.client.force_login(self.encargado)
        self.assertEqual(self.enviar(self.evento(25), 'y' * 43).status_code, 401)
        self.assertFalse(Medicion.objects.exists())

    def test_lectura_invalida_y_fecha_sin_zona(self):
        self.assertEqual(self.enviar(self.evento(101)).status_code, 400)
        dato = self.evento(10)
        dato['tomada_en'] = '2026-11-05T20:00:00'
        self.assertEqual(self.enviar(dato).status_code, 400)
        self.assertFalse(Medicion.objects.exists())

    @patch('monitoreo.push.notificar_alerta')
    def test_ciclo_agua_notifica_solo_al_cruzar(self, notificar):
        for nivel, esperado in [(78, False), (25, True), (20, False), (85, False), (25, True)]:
            with self.captureOnCommitCallbacks(execute=True):
                r = self.enviar(self.evento(nivel))
            self.assertEqual(r.status_code, 201, r.content)
            self.assertEqual(r.json()['alerta_nueva'], esperado)
        self.assertEqual(notificar.call_count, 2)
        self.assertEqual(Alerta.objects.count(), 2)
        self.assertEqual(Alerta.objects.filter(resuelta__isnull=True).count(), 1)
        self.assertEqual(Medicion.objects.latest('fecha').volumen_litros, 7500)

    def test_reintentos_y_conflicto_uuid(self):
        dato = self.evento(25)
        self.assertEqual(self.enviar(dato).status_code, 201)
        r = self.enviar(dato)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['duplicada'])
        self.assertEqual(self.enviar({**dato, 'porcentaje': '26'}).status_code, 409)
        self.assertEqual(Medicion.objects.count(), 1)
        self.assertEqual(Alerta.objects.count(), 1)

    def test_lectura_atrasada_no_altera_nivel_ni_alerta(self):
        ahora = timezone.now()
        self.enviar(self.evento(85, ahora))
        self.enviar(self.evento(25, ahora - timezone.timedelta(minutes=1)))
        self.client.force_login(self.trabajador)
        r = self.client.get(reverse('niveles_api')).json()
        self.assertEqual(r['estanques'][0]['porcentaje'], 85)
        self.assertFalse(Alerta.objects.exists())
        self.assertEqual(Medicion.objects.count(), 2)

    def test_agua_sin_lecturas_y_trabajador_sin_push(self):
        self.client.force_login(self.trabajador)
        r = self.client.get(reverse('agua'))
        self.assertContains(r, 'Sin mediciones')
        self.assertNotContains(r, 'Activar notificaciones')
        self.assertEqual(self.client.post(reverse('push_suscripcion'), {}, content_type='application/json').status_code, 403)

    def test_service_worker_y_manifiesto(self):
        r = self.client.get(reverse('service_worker'))
        self.assertContains(r, 'showNotification')
        self.assertEqual(r['Content-Type'], 'application/javascript')
        self.assertEqual(self.client.get(reverse('manifest')).json()['start_url'], '/agua/')

    @patch('monitoreo.push_views.clave_publica', return_value='configurada')
    def test_registro_y_baja_con_csrf(self, clave):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.encargado)
        url = reverse('push_suscripcion')
        self.assertEqual(browser.post(url, {}, content_type='application/json').status_code, 403)
        browser.get(reverse('alertas'))
        headers = {'X-CSRFToken': browser.cookies['csrftoken'].value}
        def post(data):
            return browser.post(url, data, content_type='application/json', headers=headers)
        def b64(value):
            return base64.urlsafe_b64encode(value).decode().rstrip('=')
        raw = generate_private_key(SECP256R1()).public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        endpoint = 'https://fcm.googleapis.com/fcm/send/prueba'
        keys = {'p256dh': b64(raw), 'auth': b64(b'a' * 16)}
        self.assertEqual(post({'endpoint': 'https://127.0.0.1/privado', 'keys': keys}).status_code, 400)
        self.assertEqual(post({'endpoint': endpoint, 'keys': keys}).status_code, 200)
        self.assertEqual(post({'endpoint': endpoint, 'keys': keys}).status_code, 200)
        self.assertEqual(SuscripcionPush.objects.count(), 1)
        self.assertEqual(post({'endpoint': endpoint, 'accion': 'quitar'}).status_code, 200)
        self.assertFalse(SuscripcionPush.objects.exists())


    @override_settings(PUSH_CONTACT='mailto:equipo@example.org', PUBLIC_ORIGIN='https://fundo.example.org')
    @patch('monitoreo.push.clave_publica', return_value='configurada')
    @patch('monitoreo.push.SinRedirecciones.post')
    @patch('monitoreo.push.Vapid.from_file')
    def test_envio_cifrado_solo_al_origen_activo(self, cargar, post, clave):
        v = Vapid()
        v.generate_keys()
        cargar.return_value = v
        post.return_value = Mock(status_code=201)
        raw = generate_private_key(SECP256R1()).public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        for index, origin in enumerate(('https://fundo.example.org', 'https://anterior.example.org')):
            SuscripcionPush.objects.create(usuario=self.encargado, origen=origin,
                endpoint_hash=str(index), endpoint=f'https://fcm.googleapis.com/fcm/send/{index}',
                p256dh=base64.urlsafe_b64encode(raw).decode().rstrip('='),
                auth=base64.urlsafe_b64encode(b'a' * 16).decode().rstrip('='))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.enviar(self.evento(25)).status_code, 201)
        post.assert_called_once()
        call = post.call_args
        self.assertEqual(call.args[0], 'https://fcm.googleapis.com/fcm/send/0')
        self.assertEqual(call.kwargs['headers']['content-encoding'], 'aes128gcm')
        self.assertIn('vapid', call.kwargs['headers']['authorization'])
        self.assertNotIn(b'Nivel bajo', call.kwargs['data'])
        self.assertEqual(Alerta.objects.get().push_aceptadas, 1)
