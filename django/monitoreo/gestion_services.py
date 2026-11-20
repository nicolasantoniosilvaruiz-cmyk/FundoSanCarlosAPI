from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .gestion_forms import EmpleadoEditarForm, EmpleadoNuevoForm, MovimientoForm
from .models import Estanque, Medicion, MovimientoPetroleo, SaldoPetroleo, SesionMovil, Usuario
from .services import ultima_medicion


def invalidar_sesiones(usuario_id):
    SesionMovil.objects.filter(usuario_id=usuario_id).delete()
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if str(session.get_decoded().get('_auth_user_id')) == str(usuario_id):
            session.delete()


@transaction.atomic
def guardar_empleado(actor, datos, empleado_id=None):
    # Todos los cambios de acceso se serializan sobre las mismas cuentas.
    list(Usuario.objects.select_for_update().order_by('pk').values_list('pk', flat=True))
    actor = Usuario.objects.get(pk=actor.pk)
    if not actor.is_active or not actor.es_administrador:
        raise PermissionDenied
    empleado = Usuario.objects.get(pk=empleado_id) if empleado_id else None
    form = EmpleadoEditarForm(datos, instance=empleado) if empleado else EmpleadoNuevoForm(datos)
    if not form.is_valid():
        return form
    if empleado and empleado.pk == actor.pk and (
        not form.cleaned_data['is_active'] or form.cleaned_data['rol'] != Usuario.Rol.ADMINISTRADOR
    ):
        form.add_error(None, 'Tu propia cuenta debe conservar acceso de administrador.')
        return form
    resultado = form.save()
    if not resultado.is_active:
        invalidar_sesiones(resultado.pk)
    return form


@transaction.atomic
def cambiar_clave(usuario, datos, sesion=None):
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    if not usuario.is_active:
        raise PermissionDenied
    form = PasswordChangeForm(usuario, datos)
    if form.is_valid():
        form.save()
        if sesion:
            # Conserva la sesión actual y su suscripción push. Las demás caducan por la huella.
            sesion.huella_usuario = usuario.get_session_auth_hash()
            sesion.save(update_fields=['huella_usuario'])
    return form


@transaction.atomic
def saldo_petroleo():
    estanque = Estanque.objects.select_for_update().get(tipo=Estanque.Tipo.PETROLEO)
    saldo = SaldoPetroleo.objects.filter(estanque=estanque).first()
    if saldo is None:
        lectura = ultima_medicion(estanque)
        litros = lectura.volumen_litros if lectura else estanque.capacidad_litros
        saldo = SaldoPetroleo.objects.create(estanque=estanque, litros=litros)
    return saldo


@transaction.atomic
def registrar_movimiento(usuario, datos):
    form = MovimientoForm(datos)
    if not form.is_valid():
        raise ValidationError(form.errors.as_text())
    dato = form.cleaned_data
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    if not usuario.is_active:
        raise PermissionDenied
    if dato['tipo'] == 'recarga' and not usuario.es_administrador:
        raise PermissionDenied
    saldo = saldo_petroleo()
    saldo = SaldoPetroleo.objects.select_for_update().select_related('estanque').get(pk=saldo.pk)
    anterior = MovimientoPetroleo.objects.filter(solicitud=dato['solicitud']).first()
    if anterior:
        if (anterior.usuario_id == usuario.pk and anterior.tipo == dato['tipo']
            and anterior.antes == dato['antes'] and anterior.cantidad == dato['cantidad']
            and anterior.despues == dato['despues']):
            return anterior, False
        raise ValidationError('La solicitud ya fue usada con otros datos.')
    if saldo.revision != dato['revision']:
        raise ValidationError('El saldo cambió. Actualiza el saldo antes de registrar el movimiento.')
    esperado = dato['antes'] + dato['cantidad'] if dato['tipo'] == 'recarga' else dato['antes'] - dato['cantidad']
    if esperado != dato['despues']:
        raise ValidationError('La cantidad inicial, el movimiento y el saldo final deben coincidir exactamente.')
    if not 0 <= esperado <= saldo.estanque.capacidad_litros:
        raise ValidationError('El saldo debe quedar entre 0 y la capacidad del estanque.')
    registro = MovimientoPetroleo.objects.create(
        solicitud=dato['solicitud'], saldo=saldo, usuario=usuario,
        identidad=f'{usuario.get_full_name() or usuario.username} ({usuario.username})',
        rut_responsable=usuario.rut or '', saldo_registrado=saldo.litros,
        tipo=dato['tipo'], antes=dato['antes'], cantidad=dato['cantidad'], despues=dato['despues'])
    saldo.litros = esperado
    saldo.revision += 1
    saldo.save(update_fields=['litros', 'revision'])
    Medicion.objects.create(estanque=saldo.estanque, volumen_litros=esperado, creada_por=usuario, simulada=True)
    return registro, True


def movimientos_visibles(usuario):
    registros = MovimientoPetroleo.objects.select_related('usuario')
    return registros if usuario.es_administrador else registros.filter(usuario=usuario)

    
def empleados_con_retiros():
    from django.db.models import Count, Q, Sum
    return Usuario.objects.annotate(
        retiros_count=Count('movimientopetroleo', filter=Q(movimientopetroleo__tipo='retiro')),
        litros_retirados=Sum('movimientopetroleo__cantidad', filter=Q(movimientopetroleo__tipo='retiro'), default=0),
    ).order_by('username')


@transaction.atomic
def configurar_capacidad_visual(capacidad):
    agua = Estanque.objects.select_for_update().get(tipo=Estanque.Tipo.AGUA)
    agua.capacidad_visual_litros = capacidad
    agua.save(update_fields=['capacidad_visual_litros'])
    return agua
