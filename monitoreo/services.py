from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Alerta, Estanque, Medicion


def evaluar_alerta(estanque, medicion):
    if estanque.tipo != Estanque.Tipo.AGUA or medicion is None:
        return False
    activas = Alerta.objects.filter(estanque=estanque, resuelta__isnull=True)
    if medicion.porcentaje < estanque.umbral_pct:
        if not activas.exists():
            Alerta.objects.create(estanque=estanque, medicion=medicion, umbral_aplicado=estanque.umbral_pct)
            return True
    else:
        activas.update(resuelta=timezone.now())
    return False


@transaction.atomic
def registrar_simulacion(estanque_id, porcentaje, usuario):
    # Serializa la evaluación de cada estanque cuando la base soporta bloqueo de filas.
    estanque = Estanque.objects.select_for_update().get(pk=estanque_id)
    porcentaje = Decimal(porcentaje)
    if not porcentaje.is_finite() or not 0 <= porcentaje <= 100:
        raise ValidationError('El porcentaje debe estar entre 0 y 100.')
    volumen = (estanque.capacidad_litros * porcentaje / 100).quantize(Decimal('0.001'))
    medicion = Medicion.objects.create(estanque=estanque, volumen_litros=volumen, simulada=True, creada_por=usuario)
    nueva_alerta = evaluar_alerta(estanque, medicion)
    return medicion, nueva_alerta


@transaction.atomic
def configurar_umbral(estanque_id, porcentaje):
    estanque = Estanque.objects.select_for_update().get(pk=estanque_id)
    estanque.umbral_pct = porcentaje
    estanque.full_clean()
    estanque.save(update_fields=['umbral_pct'])
    evaluar_alerta(estanque, estanque.mediciones.first())
    return estanque


def estado_estanque(estanque):
    medicion = estanque.mediciones.first()
    porcentaje = medicion.porcentaje if medicion else Decimal(0)
    desactualizado = medicion is None or timezone.now() - medicion.fecha > timezone.timedelta(minutes=5)
    bajo = estanque.tipo == Estanque.Tipo.AGUA and medicion is not None and porcentaje < estanque.umbral_pct
    return {
        'id': estanque.pk, 'nombre': estanque.nombre, 'tipo': estanque.tipo,
        'capacidad': float(estanque.capacidad_litros), 'umbral': float(estanque.umbral_pct),
        'volumen': float(medicion.volumen_litros) if medicion else None,
        'porcentaje': round(float(porcentaje), 2) if medicion else None,
        'fecha': medicion.fecha.isoformat() if medicion else None,
        'desactualizado': desactualizado, 'bajo': bajo, 'simulada': medicion.simulada if medicion else False,
    }
