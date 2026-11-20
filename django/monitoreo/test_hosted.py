import os
import runpy
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import Estanque, Medicion, Usuario


class HostedTests(TestCase):
    def test_health_does_not_require_login(self):
        self.assertEqual(self.client.get(reverse('salud')).json(), {'ok': True})

    def test_demo_requires_new_passwords_and_is_repeatable(self):
        with patch.dict(os.environ, {'DEMO_ADMIN_PASSWORD': 'FundoDemo2026!', 'DEMO_TRABAJADOR_PASSWORD': 'otro-exclusivo-d01'}):
            with self.assertRaises(CommandError):
                call_command('preparar_demo_publica', stdout=StringIO())
        self.assertFalse(Usuario.objects.exists())
        config = {'DEMO_ADMIN_PASSWORD': 'Montes-del-sur_971!', 'DEMO_TRABAJADOR_PASSWORD': 'Cosecha-lago_842!'}
        with patch.dict(os.environ, config):
            output = StringIO()
            call_command('preparar_demo_publica', stdout=output)
            call_command('preparar_demo_publica', stdout=output)
        self.assertNotIn(config['DEMO_ADMIN_PASSWORD'], output.getvalue())
        self.assertTrue(Usuario.objects.get(username='admin').check_password(config['DEMO_ADMIN_PASSWORD']))
        self.assertEqual(Estanque.objects.count(), 2)
        self.assertEqual(Medicion.objects.count(), 2)

    def test_hosted_configuration_uses_tls_and_postgres(self):
        settings = {
            'DJANGO_PUBLIC_ORIGIN': '',
            'RENDER_EXTERNAL_URL': 'https://demo.example.org/',
            'DJANGO_SECRET_KEY': 'z' * 50,
            'DATABASE_URL': 'postgresql://owner:temp%40pass@db.example.org:5432/fundo',
        }
        with patch.dict(os.environ, settings):
            deployed = runpy.run_module('config.hosted')
        self.assertEqual(deployed['ALLOWED_HOSTS'], ['demo.example.org'])
        self.assertEqual(deployed['CSRF_TRUSTED_ORIGINS'], ['https://demo.example.org'])
        self.assertFalse(deployed['DEBUG'])
        self.assertTrue(deployed['SECURE_SSL_REDIRECT'])
        self.assertTrue(deployed['SESSION_COOKIE_SECURE'])
        db = deployed['DATABASES']['default']
        self.assertEqual(db['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(db['PASSWORD'], 'temp@pass')
        self.assertEqual(db['OPTIONS']['sslmode'], 'require')

    def test_hosted_mode_rejects_http(self):
        with patch.dict(os.environ, {'DJANGO_PUBLIC_ORIGIN': 'http://demo.example.org'}):
            with self.assertRaises(ImproperlyConfigured):
                runpy.run_module('config.hosted')
