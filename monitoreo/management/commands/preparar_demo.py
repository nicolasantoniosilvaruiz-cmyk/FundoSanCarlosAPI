from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from monitoreo.models import Usuario, Estanque, Medicion


class Command(BaseCommand):
    help = 'Crea cuentas y estanques de demostración sin borrar mediciones ni cambiar cuentas existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        for nombre, rol, password, primero in [
            ('admin', Usuario.Rol.ADMINISTRADOR, 'FundoDemo2026!', 'Martín'),
            ('trabajador', Usuario.Rol.TRABAJADOR, 'CampoDemo2026!', 'Juan'),
        ]:
            usuario, nuevo = Usuario.objects.get_or_create(username=nombre, defaults={'rol': rol, 'first_name': primero})
            if nuevo:
                usuario.set_password(password)
                usuario.save()
                self.stdout.write(f'Cuenta creada: {nombre} / {password}')
            else:
                self.stdout.write(f'Cuenta existente conservada: {nombre}')
        for tipo, nombre, capacidad, volumen in [
            ('agua', 'Estanque de agua', '30000', '23400'),
            ('petroleo', 'Estanque de petróleo', '1000', '450'),
        ]:
            estanque, _ = Estanque.objects.get_or_create(tipo=tipo, defaults={'nombre': nombre, 'capacidad_litros': Decimal(capacidad), 'umbral_pct': 30})
            if not estanque.mediciones.exists():
                Medicion.objects.create(estanque=estanque, volumen_litros=Decimal(volumen), simulada=True)
        self.stdout.write(self.style.SUCCESS('Demostración preparada. No se borraron registros existentes.'))
