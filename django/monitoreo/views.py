from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from .forms import CapacidadVisualForm, UmbralForm, SimulacionForm
from .gestion_services import configurar_capacidad_visual
from .models import Alerta, Estanque, Medicion
from .push import clave_publica
from .services import configurar_umbral, estado_estanque, registrar_simulacion


def administrador_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.es_administrador:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


@never_cache
@login_required
def panel(request, solo_agua=False):
    estanques = Estanque.objects.filter(tipo='agua') if solo_agua else Estanque.objects.all()
    estados = [estado_estanque(e) for e in estanques]
    context = {'estados': estados, 'solo_agua': solo_agua, 'seccion': 'agua' if solo_agua else 'panel'}
    if request.user.es_administrador:
        context['alertas'] = Alerta.objects.filter(resuelta__isnull=True).select_related('medicion', 'estanque')
        context['ultimas'] = Medicion.objects.filter(estanque__in=estanques).select_related('estanque')[:8]
    return render(request, 'monitoreo/panel.html', context)


@never_cache
@login_required
def niveles_api(request):
    return JsonResponse({'estanques': [estado_estanque(e) for e in Estanque.objects.all()]})


@never_cache
@administrador_required
def alertas(request):
    agua = get_object_or_404(Estanque, tipo=Estanque.Tipo.AGUA)
    form = UmbralForm(request.POST or None, instance=agua)
    if request.method == 'POST' and form.is_valid():
        configurar_umbral(agua.pk, form.cleaned_data['umbral_pct'])
        messages.success(request, 'Umbral de agua guardado. Se aplicará a las mediciones del estanque.')
        return redirect('alertas')
    return render(request, 'monitoreo/alertas.html', {'form': form, 'agua': agua, 'historial': Alerta.objects.select_related('medicion', 'estanque')[:20], 'seccion': 'alertas', 'push_key': clave_publica()})


@never_cache
@administrador_required
def simulador(request):
    agua = get_object_or_404(Estanque, tipo=Estanque.Tipo.AGUA)
    cambia_capacidad = request.method == 'POST' and request.POST.get('accion') == 'capacidad_visual'
    capacidad_form = CapacidadVisualForm(
        request.POST if cambia_capacidad else None,
        initial={'capacidad_visual_litros': agua.capacidad_representada})
    if cambia_capacidad and capacidad_form.is_valid():
        configurar_capacidad_visual(capacidad_form.cleaned_data['capacidad_visual_litros'])
        messages.success(request, 'Capacidad de visualización actualizada.')
        return redirect('simulador')
    form = SimulacionForm(request.POST if request.method == 'POST' and not cambia_capacidad else None)
    if request.method == 'POST' and not cambia_capacidad and form.is_valid():
        medicion, nueva = registrar_simulacion(form.cleaned_data['estanque'].pk, form.cleaned_data['porcentaje'], request.user)
        estanque = medicion.estanque
        volumen = estanque.volumen_visible(medicion.volumen_litros)
        messages.success(request, f'Lectura guardada: {volumen:.0f} {estanque.unidad_volumen} en {estanque.nombre}.')
        if nueva:
            messages.warning(request, 'Se generó una alerta de nivel bajo de agua.')
        return redirect('panel')
    return render(request, 'monitoreo/simulador.html', {'form': form, 'capacidad_form': capacidad_form, 'estanques': Estanque.objects.all(), 'seccion': 'simulador'})
