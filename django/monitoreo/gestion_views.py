import uuid

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from .gestion_forms import EmpleadoEditarForm, EmpleadoNuevoForm, MovimientoForm
from .gestion_services import empleados_con_retiros, cambiar_clave, guardar_empleado, movimientos_visibles, registrar_movimiento, saldo_petroleo
from .models import Estanque, Usuario
from .views import administrador_required


@never_cache
@administrador_required
def empleados(request):
    return render(request, 'monitoreo/empleados.html', {
        'empleados': empleados_con_retiros(), 'seccion': 'empleados'})


@never_cache
@administrador_required
def empleado(request, pk=None):
    cuenta = get_object_or_404(empleados_con_retiros(), pk=pk) if pk else None
    form = EmpleadoEditarForm(instance=cuenta) if cuenta else EmpleadoNuevoForm()
    if request.method == 'POST':
        try:
            form = guardar_empleado(request.user, request.POST, pk)
        except IntegrityError:
            form = EmpleadoEditarForm(request.POST, instance=cuenta) if cuenta else EmpleadoNuevoForm(request.POST)
            form.is_valid()
            form.add_error(None, 'El usuario ya existe. Actualiza la página y revisa el nombre de usuario.')
        if form.is_valid():
            messages.success(request, 'Empleado guardado.')
            return redirect('empleados')
    return render(request, 'monitoreo/gestion_form.html', {
        'form': form, 'titulo': 'Editar empleado' if cuenta else 'Ingresar empleado',
        'volver': 'empleados', 'seccion': 'empleados', 'empleado': cuenta,
        'retiros': cuenta.movimientopetroleo_set.filter(tipo='retiro') if cuenta else []})


@never_cache
@login_required
def clave(request):
    form = PasswordChangeForm(request.user)
    if request.method == 'POST':
        form = cambiar_clave(request.user, request.POST)
        if form.is_valid():
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Contraseña actualizada.')
            return redirect('panel')
    return render(request, 'monitoreo/gestion_form.html', {
        'form': form, 'titulo': 'Cambiar contraseña', 'volver': 'panel', 'seccion': 'clave'})


@never_cache
@login_required
def petroleo(request):
    try:
        saldo = saldo_petroleo()
    except Estanque.DoesNotExist:
        raise Http404('No hay estanque de petróleo.')
    form = MovimientoForm(initial={
        'solicitud': uuid.uuid4(), 'revision': saldo.revision, 'tipo': 'retiro'})
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            try:
                registrar_movimiento(request.user, request.POST)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Movimiento registrado.')
                return redirect('petroleo')
    return render(request, 'monitoreo/petroleo.html', {
        'form': form, 'saldo': saldo, 'movimientos': movimientos_visibles(request.user)[:100],
        'seccion': 'petroleo'})
