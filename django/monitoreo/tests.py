from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from monitoreo.models import Alerta, Estanque, Medicion
from monitoreo.services import registrar_simulacion


class MonitoreoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('encargado', password='PruebaSegura2026!', rol='administrador')
        cls.worker = User.objects.create_user('operario', password='PruebaSegura2026!', rol='trabajador')
        cls.water = Estanque.objects.create(nombre='Estanque de agua', tipo='agua', capacidad_litros=30000, umbral_pct=30)
        cls.fuel = Estanque.objects.create(nombre='Estanque de petróleo', tipo='petroleo', capacidad_litros=1000, umbral_pct=30)
        registrar_simulacion(cls.water.pk, 78, cls.admin)
        registrar_simulacion(cls.fuel.pk, 45, cls.admin)

    def test_requires_login(self):
        for url in ['panel', 'alertas', 'simulador', 'niveles_api']:
            self.assertEqual(self.client.get(reverse(url)).status_code, 302)

    def test_both_roles_can_login(self):
        for username in ['encargado', 'operario']:
            self.assertTrue(self.client.login(username=username, password='PruebaSegura2026!'))
            self.assertEqual(self.client.get(reverse('panel')).status_code, 200)
            self.client.logout()

    def test_wrong_password(self):
        response = self.client.post(reverse('login'), {'username': 'encargado', 'password': 'equivocada'})
        self.assertContains(response, 'Usuario o contraseña incorrectos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_worker_cannot_access_or_change_admin_views(self):
        self.client.force_login(self.worker)
        count = Medicion.objects.count()
        for url in ['alertas', 'simulador']:
            self.assertEqual(self.client.get(reverse(url)).status_code, 403)
            self.assertEqual(self.client.post(reverse(url), {'umbral_pct': 90, 'estanque': self.water.pk, 'porcentaje': 1}).status_code, 403)
        self.water.refresh_from_db()
        self.assertEqual(self.water.umbral_pct, 30)
        self.assertEqual(Medicion.objects.count(), count)

    def test_worker_panel_has_no_admin_controls(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse('panel'))
        self.assertNotContains(response, 'Configurar umbral de alerta')
        self.assertNotContains(response, 'Últimas mediciones')
        self.assertContains(response, 'Tu acceso es de consulta')

    def test_valid_threshold_persisted(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(reverse('alertas'), {'umbral_pct': '35.5'}), reverse('alertas'))
        self.water.refresh_from_db()
        self.assertEqual(self.water.umbral_pct, Decimal('35.5'))

    def test_invalid_threshold_rejected(self):
        self.client.force_login(self.admin)
        for value in ['-1', '101', 'abc', 'NaN']:
            self.assertEqual(self.client.post(reverse('alertas'), {'umbral_pct': value}).status_code, 200)
        self.water.refresh_from_db()
        self.assertEqual(self.water.umbral_pct, 30)

    def test_conversion_and_alert_lifecycle(self):
        reading, new = registrar_simulacion(self.water.pk, 25, self.admin)
        self.assertEqual(reading.volumen_litros, Decimal('7500'))
        self.assertTrue(new)
        _, new = registrar_simulacion(self.water.pk, 20, self.admin)
        self.assertFalse(new)
        self.assertEqual(Alerta.objects.count(), 1)
        registrar_simulacion(self.water.pk, 30, self.admin)
        self.assertIsNotNone(Alerta.objects.get().resuelta)
        registrar_simulacion(self.water.pk, 25, self.admin)
        self.assertEqual(Alerta.objects.count(), 2)
        self.assertEqual(Alerta.objects.filter(resuelta__isnull=True).count(), 1)

    def test_fuel_has_no_water_alert(self):
        reading, new = registrar_simulacion(self.fuel.pk, 10, self.admin)
        self.assertEqual(reading.volumen_litros, 100)
        self.assertFalse(new)
        self.assertFalse(Alerta.objects.exists())

    def test_simulator_invalid_input_never_writes(self):
        self.client.force_login(self.admin)
        count = Medicion.objects.count()
        for value in ['-1', '101', 'NaN', 'Infinity', 'abc']:
            response = self.client.post(reverse('simulador'), {'estanque': self.water.pk, 'porcentaje': value})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(Medicion.objects.count(), count)

    def test_simulator_saves_then_redirects(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('simulador'), {'estanque': self.water.pk, 'porcentaje': '25'})
        self.assertRedirects(response, reverse('panel'))
        self.assertEqual(self.water.mediciones.first().volumen_litros, 7500)
        self.assertContains(self.client.get(reverse('panel')), 'Atención: nivel de agua bajo')

    def test_api_capacity_timestamp_and_staleness(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse('niveles_api'))
        self.assertIn('no-store', response['Cache-Control'])
        states = response.json()['estanques']
        self.assertEqual(states[0]['capacidad'], 30000)
        self.assertEqual(states[1]['capacidad'], 1000)
        self.assertEqual(states[1]['volumen'], 450)
        self.assertTrue(states[0]['simulada'])
        from django.utils import timezone
        Medicion.objects.update(fecha=timezone.now() - timezone.timedelta(minutes=6))
        self.assertTrue(self.client.get(reverse('niveles_api')).json()['estanques'][0]['desactualizado'])

    def test_post_requires_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.admin)
        self.assertEqual(browser.post(reverse('simulador'), {'estanque': self.water.pk, 'porcentaje': 25}).status_code, 403)
        self.assertEqual(browser.post(reverse('alertas'), {'umbral_pct': 25}).status_code, 403)

    def test_logout_is_post_only(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_demo_command_does_not_destroy_data(self):
        import io
        call_command('preparar_demo', stdout=io.StringIO())
        count = Medicion.objects.count()
        call_command('preparar_demo', stdout=io.StringIO())
        self.assertEqual(Medicion.objects.count(), count)
        self.assertEqual(Estanque.objects.count(), 2)
