from django.contrib.auth import views as auth_views
from django.urls import path
from . import views, api_agua, api_movil, push_views
from .forms import IngresoForm
from .salud import salud
from . import gestion_views, gestion_api

urlpatterns = [
    path('api/movil/capacidad-visual/', gestion_api.capacidad_visual, name='movil_capacidad_visual'),
    path('empleados/', gestion_views.empleados, name='empleados'),
    path('empleados/nuevo/', gestion_views.empleado, name='empleado_nuevo'),
    path('empleados/<int:pk>/', gestion_views.empleado, name='empleado'),
    path('cuenta/clave/', gestion_views.clave, name='cambiar_clave'),
    path('petroleo/', gestion_views.petroleo, name='petroleo'),
    path('api/movil/empleados/', gestion_api.empleados, name='movil_empleados'),
    path('api/movil/empleado/', gestion_api.empleado, name='movil_empleado'),
    path('api/movil/clave/', gestion_api.clave, name='movil_clave'),
    path('api/movil/petroleo/', gestion_api.petroleo, name='movil_petroleo'),
    path('api/movil/movimiento/', gestion_api.movimiento, name='movil_movimiento'),
    path('salud/', salud, name='salud'),
    path('', views.panel, name='panel'),
    path('agua/', views.panel, {'solo_agua': True}, name='agua'),
    path('api/movil/ingresar/', api_movil.ingresar, name='movil_ingresar'),
    path('api/movil/salir/', api_movil.salir, name='movil_salir'),
    path('api/movil/panel/', api_movil.panel, name='movil_panel'),
    path('api/movil/umbral/', api_movil.umbral, name='movil_umbral'),
    path('api/movil/lectura/', api_movil.lectura, name='movil_lectura'),
    path('api/movil/notificaciones/', api_movil.notificaciones, name='movil_notificaciones'),
    path('api/agua/mediciones/', api_agua.recibir_agua, name='recibir_agua'),
    path('api/push/suscripcion/', push_views.suscripcion, name='push_suscripcion'),
    path('service-worker.js', push_views.service_worker, name='service_worker'),
    path('manifest.webmanifest', push_views.manifest, name='manifest'),
    path('ingresar/', auth_views.LoginView.as_view(template_name='registration/login.html', authentication_form=IngresoForm, redirect_authenticated_user=True), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('alertas/', views.alertas, name='alertas'),
    path('simulador/', views.simulador, name='simulador'),
    path('api/niveles/', views.niveles_api, name='niveles_api'),
]
