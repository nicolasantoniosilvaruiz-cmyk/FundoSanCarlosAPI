from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from monitoreo.models import Estanque, Medicion


class Command(BaseCommand):
    help = 'Configura 1 L de capacidad para el prototipo de agua y convierte sus lecturas a escala.'

    @transaction.atomic
    def handle(self, *args, **options):
        agua = Estanque.objects.select_for_update().filter(tipo=Estanque.Tipo.AGUA).first()
        if agua is None:
            raise CommandError('No existe el estanque de agua. Ejecuta preparar_demo primero.')
        capacidad = Decimal('1.000')
        if agua.capacidad_litros == capacidad:
            self.stdout.write('El estanque de agua ya tiene capacidad de 1.000 mL.')
            return
        factor = capacidad / agua.capacidad_litros
        mediciones = list(agua.mediciones.all())
        for medicion in mediciones:
            medicion.volumen_litros = (medicion.volumen_litros * factor).quantize(Decimal('0.001'))
        Medicion.objects.bulk_update(mediciones, ['volumen_litros'], batch_size=500)
        agua.capacidad_litros = capacidad
        agua.save(update_fields=['capacidad_litros'])
        self.stdout.write(self.style.SUCCESS(f'Capacidad de agua: 1.000 mL. Lecturas convertidas: {len(mediciones)}.'))
