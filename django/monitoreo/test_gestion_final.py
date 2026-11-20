from decimal import Decimal
import uuid

from django.contrib.auth import get_user
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .api_movil import digest
from .gestion_services import guardar_empleado, movimientos_visibles, registrar_movimiento, saldo_petroleo
from .models import Estanque, Medicion, MovimientoPetroleo, SesionMovil, Usuario
from .services import estado_estanque


class GestionFinalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user('jefe', password='InicioFuerte-827!', rol='administrador')
        cls.worker = Usuario.objects.create_user('campo', password='InicioFuerte-827!', rol='trabajador', rut='12345678-5')
        cls.other = Usuario.objects.create_user('otro', password='InicioFuerte-827!', rol='trabajador')
        cls.water = Estanque.objects.create(tipo='agua', nombre='Agua', capacidad_litros=1)
        cls.fuel = Estanque.objects.create(tipo='petroleo', nombre='Petróleo', capacidad_litros=1000)
        Medicion.objects.create(estanque=cls.water, volumen_litros=Decimal('0.800'), simulada=False)
        Medicion.objects.create(estanque=cls.fuel, volumen_litros=450, simulada=True)

    def event(self, **changes):
        data = {'solicitud': str(uuid.uuid4()), 'revision': saldo_petroleo().revision,
                'tipo': 'retiro', 'antes': '1000', 'cantidad': '100', 'despues': '900'}
        data.update(changes)
        return data

    def token(self, user):
        response = self.client.post(reverse('movil_ingresar'), {
            'usuario': user.username, 'contrasena': 'InicioFuerte-827!'}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['token']

    def post(self, route, token, data):
        return self.client.post(reverse(route), data, content_type='application/json',
                                headers={'Authorization': f'Bearer {token}'})

    def edit_data(self, user, **changes):
        data = {'username': user.username, 'first_name': 'Empleado', 'last_name': 'Campo',
                'rut': user.rut or '', 'email': 'persona@example.org', 'rol': user.rol, 'is_active': True}
        data.update(changes)
        return data

    def test_retiro_manual_arbitrario_y_reintento(self):
        dato = self.event()
        registro, nuevo = registrar_movimiento(self.worker, dato)
        self.assertTrue(nuevo)
        self.assertEqual(registro.saldo_registrado, 450)
        self.assertEqual(registro.antes, 1000)
        self.assertEqual(registro.rut_responsable, '12345678-5')
        self.assertEqual(estado_estanque(self.fuel)['volumen'], 900)
        self.assertFalse(registrar_movimiento(self.worker, dato)[1])
        self.assertEqual(MovimientoPetroleo.objects.count(), 1)
        self.assertEqual(estado_estanque(self.water)['volumen'], 0.8)

    def test_resta_invalida_y_limites_no_cambian_saldo(self):
        for cambios in ({'despues': '899'}, {'antes': '1001', 'despues': '901'},
                        {'cantidad': '-1'}, {'cantidad': '0'}, {'antes': 'NaN'},
                        {'despues': '-1'}, {'cantidad': '1.0001'}):
            with self.assertRaises(ValidationError):
                registrar_movimiento(self.worker, self.event(**cambios))
        self.assertEqual(saldo_petroleo().litros, 450)
        self.assertFalse(MovimientoPetroleo.objects.exists())

    def test_decimales_y_control_de_concurrencia(self):
        primero = self.event(antes='0.300', cantidad='0.200', despues='0.100')
        simultaneo = self.event()
        registrar_movimiento(self.worker, primero)
        with self.assertRaises(ValidationError):
            registrar_movimiento(self.other, simultaneo)
        self.assertEqual(saldo_petroleo().litros, Decimal('0.100'))

    def test_recarga_solo_admin_y_historial_propio(self):
        recarga = self.event(tipo='recarga', antes='450', cantidad='550', despues='1000')
        with self.assertRaises(PermissionDenied):
            registrar_movimiento(self.worker, recarga)
        registrar_movimiento(self.admin, recarga)
        registrar_movimiento(self.worker, self.event())
        self.assertEqual(movimientos_visibles(self.worker).count(), 1)
        self.assertEqual(movimientos_visibles(self.other).count(), 0)
        self.assertEqual(movimientos_visibles(self.admin).count(), 2)

    def test_uuid_no_se_puede_reutilizar_con_otro_actor_o_datos(self):
        data = self.event()
        registrar_movimiento(self.worker, data)
        with self.assertRaises(ValidationError):
            registrar_movimiento(self.other, data)
        with self.assertRaises(ValidationError):
            registrar_movimiento(self.worker, {**data, 'cantidad': '200', 'despues': '800'})

    def test_creacion_edicion_consulta_y_desactivacion(self):
        token = self.token(self.admin)
        data = {'username': 'nueva', 'first_name': 'Ana', 'last_name': 'Soto', 'rut': '12.345.678-5',
                'email': 'ana@example.org', 'rol': 'trabajador', 'password1': 'ClaveFirme-973!',
                'password2': 'ClaveFirme-973!'}
        # RUT existente se rechaza.
        self.assertEqual(self.post('movil_empleado', token, data).status_code, 400)
        data['rut'] = '11.111.111-1'
        response = self.post('movil_empleado', token, data)
        self.assertEqual(response.status_code, 201, response.content)
        user = Usuario.objects.get(username='nueva')
        self.assertEqual(user.rut, '11111111-1')
        self.assertTrue(user.check_password(data['password1']))
        response = self.post('movil_empleado', token, {
            'id': user.pk, **self.edit_data(user, first_name='Andrea', is_active=False)})
        self.assertEqual(response.status_code, 200, response.content)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Andrea')
        self.assertFalse(user.is_active)
        result = self.client.get(reverse('movil_empleados'), headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(result.status_code, 200)

    def test_acceso_trabajador_y_desactivacion_revocan_sesiones(self):
        token = self.token(self.worker)
        self.assertEqual(self.post('movil_empleado', token, {}).status_code, 403)
        browser = Client()
        browser.force_login(self.worker)
        registrar_movimiento(self.worker, self.event())
        guardar_empleado(self.admin, self.edit_data(self.worker, is_active=False), self.worker.pk)
        self.assertEqual(self.post('movil_movimiento', token, self.event()).status_code, 401)
        self.assertEqual(browser.get(reverse('petroleo')).status_code, 302)
        guardar_empleado(self.admin, self.edit_data(self.worker, is_active=True), self.worker.pk)
        self.assertEqual(browser.get(reverse('petroleo')).status_code, 302)
        self.assertEqual(MovimientoPetroleo.objects.count(), 1)

    def test_admin_no_puede_quitar_su_propio_acceso(self):
        form = guardar_empleado(self.admin, self.edit_data(self.admin, is_active=False), self.admin.pk)
        self.assertFalse(form.is_valid())
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_cambio_clave_android_conserva_sesion_actual_y_revoca_otra(self):
        token = self.token(self.worker)
        otro = self.token(self.worker)
        form = {'old_password': 'InicioFuerte-827!', 'new_password1': 'NuevaSegura-932!',
                'new_password2': 'NuevaSegura-932!'}
        self.assertEqual(self.post('movil_clave', token, {**form, 'old_password': 'incorrecta'}).status_code, 400)
        self.assertEqual(self.post('movil_clave', token, form).status_code, 200)
        for value, expected in [(token, 200), (otro, 401)]:
            response = self.client.get(reverse('movil_panel'), headers={'Authorization': f'Bearer {value}'})
            self.assertEqual(response.status_code, expected)
        self.worker.refresh_from_db()
        self.assertTrue(self.worker.check_password('NuevaSegura-932!'))

    def test_vistas_web_y_csrf(self):
        self.client.force_login(self.admin)
        for url in ('empleados', 'empleado_nuevo', 'cambiar_clave', 'petroleo'):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.client.force_login(self.worker)
        self.assertEqual(self.client.get(reverse('empleados')).status_code, 403)
        self.assertEqual(self.client.get(reverse('petroleo')).status_code, 200)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.worker)
        self.assertEqual(browser.post(reverse('petroleo'), self.event()).status_code, 403)

    def test_movimiento_web_se_refleja_en_api_y_viceversa(self):
        self.client.force_login(self.worker)
        response = self.client.post(reverse('petroleo'), self.event())
        self.assertEqual(response.status_code, 302, response.content)
        token = self.token(self.worker)
        api = self.client.get(reverse('movil_petroleo'), headers={'Authorization': f'Bearer {token}'}).json()
        self.assertEqual(Decimal(api['saldo']), Decimal('900'))
        response = self.post('movil_movimiento', token, self.event(antes='900', cantidad='50', despues='850'))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertContains(self.client.get(reverse('petroleo')), '850')

    def test_cambio_clave_web_conserva_sesion_y_rechaza_anterior(self):
        self.client.force_login(self.worker)
        response = self.client.post(reverse('cambiar_clave'), {
            'old_password': 'InicioFuerte-827!', 'new_password1': 'CambioWeb-973!',
            'new_password2': 'CambioWeb-973!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('petroleo')).status_code, 200)
        self.worker.refresh_from_db()
        self.assertTrue(self.worker.check_password('CambioWeb-973!'))

    
    def test_ficha_empleado_cuenta_retiros_y_excluye_recargas_y_duplicados(self):
        dato = self.event(cantidad='25.500', despues='974.500')
        registrar_movimiento(self.worker, dato)
        registrar_movimiento(self.worker, dato)
        registrar_movimiento(self.worker, self.event(antes='974.500', cantidad='10', despues='964.500'))
        registrar_movimiento(self.admin, self.event(tipo='recarga', antes='964.500', cantidad='35.500', despues='1000'))
        token = self.token(self.admin)
        listado = self.client.get(reverse('movil_empleados'), headers={'Authorization': f'Bearer {token}'}).json()
        empleado = next(e for e in listado['empleados'] if e['id'] == self.worker.pk)
        self.assertEqual(empleado['retiros_count'], 2)
        self.assertEqual(Decimal(empleado['litros_retirados']), Decimal('35.500'))
        consulta = self.post('movil_empleado', token, {'id': self.worker.pk, 'accion': 'consultar'})
        self.assertEqual(consulta.status_code, 200)
        self.assertEqual(len(consulta.json()['retiros']), 2)
        self.client.force_login(self.admin)
        ficha = self.client.get(reverse('empleado', args=[self.worker.pk]))
        self.assertEqual(ficha.context['empleado'].retiros_count, 2)
        self.assertEqual(ficha.context['empleado'].litros_retirados, Decimal('35.500'))
        self.assertContains(ficha, 'Retiros registrados')
        self.assertContains(ficha, 'Total retirado')
        ajeno = self.client.get(reverse('empleado', args=[self.other.pk]))
        self.assertEqual(ajeno.context['empleado'].retiros_count, 0)
        self.assertContains(ajeno, 'todavía no tiene retiros')
        worker_token = self.token(self.worker)
        self.assertEqual(self.post('movil_empleado', worker_token, {'id': self.admin.pk, 'accion': 'consultar'}).status_code, 403)

    
    def test_capacidad_visual_conserva_medicion_porcentaje_y_alertas(self):
        from .api_agua import hash_token
        from .models import Alerta, DispositivoAgua
        from django.utils import timezone

        token = self.token(self.admin)
        originales = list(self.water.mediciones.values_list('pk', 'volumen_litros'))
        response = self.post('movil_capacidad_visual', token, {'capacidad_visual_litros': '30000'})
        self.assertEqual(response.status_code, 200, response.content)
        self.water.refresh_from_db()
        self.assertEqual(self.water.capacidad_litros, 1)
        self.assertEqual(self.water.umbral_pct, 30)
        self.assertEqual(list(self.water.mediciones.values_list('pk','volumen_litros')), originales)
        estado = estado_estanque(self.water)
        self.assertEqual(estado['porcentaje'], 80)
        self.assertEqual(estado['capacidad_visible'], 30000)
        self.assertEqual(estado['volumen_visible'], 24000)
        self.assertEqual(estado['unidad_volumen'], 'L')
        self.assertFalse(Alerta.objects.exists())
        secret = 'v' * 43
        DispositivoAgua.objects.create(codigo='agua-real', estanque=self.water, token_hash=hash_token(secret), simulador=False)
        result = self.client.post(reverse('recibir_agua'), {
            'id': str(uuid.uuid4()), 'porcentaje': '25.00', 'tomada_en': timezone.now().isoformat()},
            content_type='application/json', headers={'X-Dispositivo': 'agua-real', 'Authorization': 'Bearer '+secret})
        self.assertEqual(result.status_code, 201, result.content)
        self.assertTrue(result.json()['alerta_nueva'])
        self.assertEqual(self.water.mediciones.first().volumen_litros, Decimal('0.250'))
        self.assertFalse(self.water.mediciones.first().simulada)
        self.assertEqual(estado_estanque(self.water)['volumen_visible'], 7500)
        self.assertEqual(estado_estanque(self.water)['porcentaje'], 25)

    def test_capacidad_visual_web_permisos_validacion_y_regreso_a_mililitros(self):
        worker = self.token(self.worker)
        self.assertEqual(self.post('movil_capacidad_visual', worker, {'capacidad_visual_litros':'30000'}).status_code, 403)
        token = self.token(self.admin)
        for value in ('0','-1','NaN','Infinity','0.0001','1000000000'):
            self.assertEqual(self.post('movil_capacidad_visual', token, {'capacidad_visual_litros':value}).status_code, 400)
        self.client.force_login(self.admin)
        count = Medicion.objects.count()
        for capacity, unit, volume in [('30000','L',24000),('1','mL',800)]:
            response = self.client.post(reverse('simulador'), {'accion':'capacidad_visual','capacidad_visual_litros':capacity})
            self.assertEqual(response.status_code, 302, response.content)
            self.water.refresh_from_db()
            state = estado_estanque(self.water)
            self.assertEqual(state['unidad_volumen'], unit)
            self.assertEqual(state['volumen_visible'], volume)
            self.assertEqual(state['porcentaje'], 80)
            self.assertEqual(Medicion.objects.count(), count)
        self.assertContains(self.client.get(reverse('simulador')), 'Guardar capacidad')
