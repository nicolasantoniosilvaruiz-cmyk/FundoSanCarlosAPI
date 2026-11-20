import re
import secrets

from django.core.management.base import BaseCommand, CommandError

from monitoreo.api_agua import hash_token
from monitoreo.models import DispositivoAgua, Estanque


class Command(BaseCommand):
    help = 'Registra un emisor de agua y muestra su token. Ejecutarlo de nuevo rota ese token.'

    def add_arguments(self, parser):
        parser.add_argument('--codigo', default='agua-simulador')
        parser.add_argument('--real', action='store_true', help='Marca al dispositivo como físico.')

    def handle(self, *args, **options):
        codigo = options['codigo']
        if not re.fullmatch(r'[a-z0-9-]{1,50}', codigo):
            raise CommandError('Usa hasta 50 letras minúsculas, números y guiones.')
        agua = Estanque.objects.filter(tipo='agua').first()
        if not agua:
            raise CommandError('Primero crea el estanque con preparar_demo.')
        token = secrets.token_urlsafe(32)
        DispositivoAgua.objects.update_or_create(codigo=codigo, defaults={
            'estanque': agua, 'token_hash': hash_token(token), 'activo': True,
            'simulador': not options['real'],
        })
        self.stdout.write(f'Dispositivo: {codigo}')
        self.stdout.write(f'Token (guárdalo en privado): {token}')
