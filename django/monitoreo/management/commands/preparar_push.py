from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from py_vapid import Vapid


class Command(BaseCommand):
    help = 'Genera las claves Web Push locales si aún no existen.'

    def handle(self, *args, **options):
        key = settings.PUSH_KEY_FILE
        if key.exists():
            self.stdout.write('Se conservaron las claves Web Push existentes.')
            return
        v = Vapid()
        v.generate_keys()
        try:
            with key.open('xb') as f:
                f.write(v.private_pem())
        except OSError as exc:
            raise CommandError('No se pudo guardar la clave privada.') from exc
        self.stdout.write(self.style.SUCCESS('Claves Web Push generadas. No compartas .push-vapid.pem.'))
