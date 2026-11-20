import uuid

from django.core.management.base import BaseCommand, CommandError

from monitoreo.gestion_services import registrar_movimiento, saldo_petroleo
from monitoreo.models import MovimientoPetroleo, Usuario


class Command(BaseCommand):
    help = 'Registra una sola recarga inicial para llenar el estanque de petróleo.'

    def handle(self, *args, **options):
        solicitud = uuid.uuid5(uuid.NAMESPACE_URL, 'fundosancarlos:petroleo:recarga-inicial')
        if MovimientoPetroleo.objects.filter(solicitud=solicitud).exists():
            self.stdout.write('La recarga inicial ya está registrada.')
            return
        saldo = saldo_petroleo()
        if saldo.movimientos.exists():
            raise CommandError('Ya hay movimientos. Registra una recarga desde el módulo Petróleo.')
        admin = Usuario.objects.filter(rol='administrador', is_active=True).order_by('pk').first()
        if not admin:
            raise CommandError('Se necesita una cuenta administradora activa.')
        cantidad = saldo.estanque.capacidad_litros - saldo.litros
        if cantidad <= 0:
            self.stdout.write('El estanque ya está lleno.')
            return
        registrar_movimiento(admin, {
            'solicitud': str(solicitud), 'revision': saldo.revision, 'tipo': 'recarga',
            'antes': str(saldo.litros), 'cantidad': str(cantidad),
            'despues': str(saldo.estanque.capacidad_litros)})
        self.stdout.write(self.style.SUCCESS(f'Recarga inicial registrada: {cantidad} L. Saldo: 1.000 L.'))
