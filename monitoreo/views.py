from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from .forms import UmbralForm, SimulacionForm
from .models import Alerta, Estanque, Medicion
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
def panel(request):
    estados = [estado_estanque(e) for e in Estanque.objects.all()]
    context = {'estados': estados, 'seccion': 'panel'}
    if request.user.es_administrador:
        context['alertas'] = Alerta.objects.filter(resuelta__isnull=True).select_related('medicion', 'estanque')
        context['ultimas'] = Medicion.objects.select_related('estanque')[:8]
    return render(request, 'monitoreo/panel.html', context)


@never_cache
@login_required
def niveles_api(request):
    # Este endpoint es de consulta para la interfaz; aún no recibe datos de ESP32.
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
    return render(request, 'monitoreo/alertas.html', {'form': form, 'agua': agua, 'historial': Alerta.objects.select_related('medicion')[:20], 'seccion': 'alertas'})


@never_cache
@administrador_required
def simulador(request):
    form = SimulacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        medicion, nueva = registrar_simulacion(form.cleaned_data['estanque'].pk, form.cleaned_data['porcentaje'], request.user)
        messages.success(request, f'Lectura guardada: {medicion.volumen_litros:,.0f} L en {medicion.estanque.nombre}.')
        if nueva:
            messages.warning(request, 'Se generó una alerta de nivel bajo de agua.')
        return redirect('panel')
    return render(request, 'monitoreo/simulador.html', {'form': form, 'seccion': 'simulador'})
