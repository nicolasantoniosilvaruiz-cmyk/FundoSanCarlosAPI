from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Estanque, Medicion, Usuario
from .services import estado_estanque


class AguaDemoTests(TestCase):
    def test_conversion_conserva_porcentajes_y_muestra_mililitros(self):
        agua = Estanque.objects.create(tipo='agua', nombre='Agua', capacidad_litros=30000)
        petroleo = Estanque.objects.create(tipo='petroleo', nombre='Combustible', capacidad_litros=1000)
        lectura = Medicion.objects.create(estanque=agua, volumen_litros=7500)
        call_command('configurar_agua_demo', stdout=StringIO())
        call_command('configurar_agua_demo', stdout=StringIO())

        agua.refresh_from_db()
        lectura.refresh_from_db()
        self.assertEqual(agua.capacidad_litros, Decimal('1.000'))
        self.assertEqual(lectura.volumen_litros, Decimal('0.250'))
        estado = estado_estanque(agua)
        self.assertEqual(estado['porcentaje'], 25)
        self.assertEqual(estado['volumen'], 0.25)
        self.assertEqual(estado['volumen_visible'], 250)
        self.assertEqual(estado['unidad_volumen'], 'mL')
        self.assertEqual(estado_estanque(petroleo)['unidad_volumen'], 'L')

        self.client.force_login(Usuario.objects.create_user(username='demo-test', rol='administrador'))
        self.assertContains(self.client.get(reverse('agua')), '250 <small>mL</small>')
        self.assertContains(self.client.get(reverse('alertas')), 'mL')
