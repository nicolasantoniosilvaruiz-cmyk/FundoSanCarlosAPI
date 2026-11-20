from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .api_movil import autenticado, error, json_body, solo_admin
from .gestion_services import empleados_con_retiros, cambiar_clave, guardar_empleado, movimientos_visibles, registrar_movimiento, saldo_petroleo
from .models import Estanque, Usuario
from .forms import CapacidadVisualForm
from .gestion_services import configurar_capacidad_visual


def cuenta(usuario):
    return {'id': usuario.pk, 'username': usuario.username, 'first_name': usuario.first_name,
            'last_name': usuario.last_name, 'rut': usuario.rut or '', 'email': usuario.email,
            'rol': usuario.rol, 'is_active': usuario.is_active,
            'retiros_count': getattr(usuario, 'retiros_count', 0),
            'litros_retirados': str(getattr(usuario, 'litros_retirados', 0))}


@require_GET
@autenticado
@solo_admin
def empleados(request):
    return JsonResponse({'empleados': [cuenta(u) for u in empleados_con_retiros()]})


@csrf_exempt
@require_POST
@autenticado
@solo_admin
def empleado(request):
    data = json_body(request) or {}
    pk = data.get('id')
    if pk is not None and (type(pk) is not int or pk <= 0):
        return error('Empleado inválido.', 400)
    if data.get('accion') == 'consultar':
        usuario = empleados_con_retiros().filter(pk=pk).first()
        if usuario is None:
            return error('Empleado no encontrado.', 404)
        resultado = cuenta(usuario)
        resultado['retiros'] = [
            {'fecha': m.fecha.isoformat(), 'antes': str(m.antes),
             'cantidad': str(m.cantidad), 'despues': str(m.despues)}
            for m in usuario.movimientopetroleo_set.filter(tipo='retiro')]
        return JsonResponse(resultado)
    try:
        form = guardar_empleado(request.usuario_movil, data, pk)
    except Usuario.DoesNotExist:
        return error('Empleado no encontrado.', 404)
    except IntegrityError:
        return error('El nombre de usuario ya está ocupado.', 409)
    if not form.is_valid():
        return error(' '.join(message for errors in form.errors.values() for message in errors), 400)
    return JsonResponse(cuenta(empleados_con_retiros().get(pk=form.instance.pk)), status=200 if pk else 201)


@csrf_exempt
@require_POST
@autenticado
def clave(request):
    form = cambiar_clave(request.usuario_movil, json_body(request) or {}, request.sesion_movil)
    if not form.is_valid():
        return error(' '.join(message for errors in form.errors.values() for message in errors), 400)
    return JsonResponse({'ok': True})


@require_GET
@autenticado
def petroleo(request):
    try:
        saldo = saldo_petroleo()
    except Estanque.DoesNotExist:
        return error('No hay estanque de petróleo.', 404)
    return JsonResponse({
        'saldo': str(saldo.litros), 'capacidad': str(saldo.estanque.capacidad_litros), 'revision': saldo.revision,
        'movimientos': [
            {'id': m.pk, 'fecha': m.fecha.isoformat(), 'responsable': m.identidad,
             'rut': m.rut_responsable, 'saldo_registrado': str(m.saldo_registrado),
             'tipo': m.tipo, 'antes': str(m.antes), 'cantidad': str(m.cantidad), 'despues': str(m.despues)}
            for m in movimientos_visibles(request.usuario_movil)[:100]]})


@csrf_exempt
@require_POST
@autenticado
def movimiento(request):
    try:
        registro, nuevo = registrar_movimiento(request.usuario_movil, json_body(request) or {})
    except ValidationError as exc:
        return error(' '.join(exc.messages), 400)
    except Estanque.DoesNotExist:
        return error('No hay estanque de petróleo.', 404)
    return JsonResponse({'id': registro.pk, 'duplicado': not nuevo}, status=201 if nuevo else 200)


@csrf_exempt
@require_POST
@autenticado
@solo_admin
def capacidad_visual(request):
    form = CapacidadVisualForm(json_body(request) or {})
    if not form.is_valid():
        return error('Ingresa una capacidad mayor que cero, con hasta tres decimales.', 400)
    try:
        agua = configurar_capacidad_visual(form.cleaned_data['capacidad_visual_litros'])
    except Estanque.DoesNotExist:
        return error('No hay estanque de agua.', 404)
    return JsonResponse({'capacidad_visual_litros': str(agua.capacidad_representada)})
