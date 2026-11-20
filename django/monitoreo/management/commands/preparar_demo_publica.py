"""Crea datos de presentación independientes, sin contraseñas de ejemplo."""
import os
from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from monitoreo.models import Estanque, Medicion, Usuario


class Command(BaseCommand):
    help = 'Prepara una base de demostración alojada con contraseñas configuradas por el propietario.'

    @transaction.atomic
    def handle(self, *args, **options):
        cuentas = [
            ('admin', Usuario.Rol.ADMINISTRADOR, 'DEMO_ADMIN_PASSWORD', 'FundoDemo2026!'),
            ('trabajador', Usuario.Rol.TRABAJADOR, 'DEMO_TRABAJADOR_PASSWORD', 'CampoDemo2026!'),
        ]
        for nombre, rol, env, clave_antigua in cuentas:
            existente = Usuario.objects.filter(username=nombre).first()
            if existente:
                if existente.check_password(clave_antigua):
                    raise CommandError(f'Restablece la contraseña de {nombre} antes de publicar.')
                continue
            password = os.environ.get(env, '')
            usuario = Usuario(username=nombre, rol=rol)
            if len(password) < 12 or password in {x[3] for x in cuentas}:
                raise CommandError(f'{env} debe tener una contraseña nueva de al menos 12 caracteres.')
            try:
                validate_password(password, usuario)
            except ValidationError as exc:
                raise CommandError(f'{env}: elige una contraseña más robusta.') from exc
            usuario.set_password(password)
            usuario.save()
        for tipo, nombre, capacidad, volumen in [
            ('agua', 'Estanque de agua', 30000, 23400), ('petroleo', 'Estanque de petróleo', 1000, 450),
        ]:
            estanque, _ = Estanque.objects.get_or_create(
                tipo=tipo, defaults={'nombre': nombre, 'capacidad_litros': Decimal(capacidad), 'umbral_pct': 30})
            if not estanque.mediciones.exists():
                Medicion.objects.create(estanque=estanque, volumen_litros=volumen, simulada=True)
        self.stdout.write('Base de presentación preparada.')
