from unittest.mock import Mock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Alerta, Estanque, Medicion, SesionMovil, Usuario


class MovilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user('admin-movil', password='ClaveLocal-fuerte87', rol='administrador')
        cls.worker = Usuario.objects.create_user('operario-movil', password='ClaveLocal-fuerte87', rol='trabajador')
        cls.agua = Estanque.objects.create(nombre='Estanque de agua', tipo='agua', capacidad_litros=30000)
        Estanque.objects.create(nombre='Estanque de petróleo', tipo='petroleo', capacidad_litros=1000)

    def login(self, user):
        response = self.client.post(reverse('movil_ingresar'), {'usuario': user.username, 'contrasena': 'ClaveLocal-fuerte87'}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['token']

    def post(self, name, token, data):
        return self.client.post(reverse(name), data, content_type='application/json',
                                headers={'Authorization': f'Bearer {token}'})

    def get(self, token):
        return self.client.get(reverse('movil_panel'), headers={'Authorization': f'Bearer {token}'})

    def test_permisos_de_trabajador_y_sesion_bearer(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('movil_panel')).status_code, 401)
        token = self.login(self.worker)
        panel = self.get(token).json()
        self.assertEqual(panel['rol'], 'trabajador')
        self.assertEqual(len(panel['estanques']), 2)
        self.assertNotIn('umbral', panel['estanques'][0])
        self.assertEqual(panel['lecturas'], [])
        for endpoint, data in [('movil_umbral', {'porcentaje': 40}),
                               ('movil_lectura', {'porcentaje': 25, 'tipo': 'agua'}),
                               ('movil_notificaciones', {'token': 'b'*32})]:
            self.assertEqual(self.post(endpoint, token, data).status_code, 403)
        self.assertFalse(Medicion.objects.exists())

    @patch('monitoreo.fcm.enviar_alerta_android')
    def test_movil_y_web_comparten_umbral_lecturas_y_alerta(self, enviar):
        token = self.login(self.admin)
        self.assertEqual(self.post('movil_umbral', token, {'porcentaje': '31.5'}).status_code, 200)
        self.client.force_login(self.admin)
        web = self.client.get(reverse('niveles_api')).json()
        self.assertEqual(web['estanques'][0]['umbral'], 31.5)
        for nivel, esperado in [(78, False), (25, True), (20, False), (85, False)]:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.post('movil_lectura', token, {'tipo':'agua','porcentaje':nivel})
            self.assertEqual(response.status_code, 201, response.content)
            self.assertEqual(response.json()['alerta_nueva'], esperado)
        enviar.assert_called_once()
        self.assertEqual(self.get(token).json()['estanques'][0]['porcentaje'], 85)
        self.assertTrue(self.get(token).json()['alertas'][0]['resuelta'])

    def test_logout_revoca_token_y_cambio_de_clave_revoca_otros(self):
        primero = self.login(self.admin)
        segundo = self.login(self.admin)
        self.assertEqual(self.post('movil_salir', primero, {}).status_code, 200)
        self.assertEqual(self.get(primero).status_code, 401)
        self.assertEqual(self.get(segundo).status_code, 200)
        self.admin.set_password('otra-clave-local-90')
        self.admin.save()
        self.assertEqual(self.get(segundo).status_code, 401)

    @patch('monitoreo.api_movil.configurado', return_value=True)
    def test_vincular_y_quitar_un_telefono(self, _):
        token = self.login(self.admin)
        otro = self.login(self.admin)
        for sesion in (token, otro):
            self.assertEqual(self.post('movil_notificaciones', sesion, {'token':'telefono:token-1234567890'}).status_code, 200)
        self.assertEqual(SesionMovil.objects.filter(fcm_hash__isnull=False).count(), 1)
        self.assertFalse(self.get(token).json()['notificaciones_vinculadas'])
        self.assertTrue(self.get(otro).json()['notificaciones_vinculadas'])
        self.assertEqual(self.post('movil_notificaciones', otro, {'accion':'quitar'}).status_code, 200)
        self.assertFalse(self.get(otro).json()['notificaciones_vinculadas'])

    @override_settings(FCM_PROJECT_ID='san-carlos-prueba', FCM_CREDENTIALS='local-no-usado.json')
    @patch('monitoreo.fcm.configurado', return_value=True)
    @patch('monitoreo.api_movil.configurado', return_value=True)
    @patch('google.oauth2.service_account.Credentials.from_service_account_file')
    @patch('google.auth.transport.requests.AuthorizedSession')
    def test_fcm_usa_alerta_confirmada_y_registra_envio(self, transport, credentials, ready1, ready2):
        token = self.login(self.admin)
        self.post('movil_notificaciones', token, {'token':'telefono:token-1234567890'})
        post = transport.return_value.__enter__.return_value.post
        post.return_value = Mock(ok=True, status_code=200)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.post('movil_lectura', token, {'tipo':'agua','porcentaje':25}).status_code, 201)
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs['json']['message']['android']['notification']['channel_id'],'alertas_agua')
        self.assertEqual(Alerta.objects.get().fcm_aceptadas, 1)
