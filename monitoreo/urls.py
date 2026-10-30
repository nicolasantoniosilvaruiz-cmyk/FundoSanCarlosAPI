from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import IngresoForm

urlpatterns = [
    path('', views.panel, name='panel'),
    path('ingresar/', auth_views.LoginView.as_view(template_name='registration/login.html', authentication_form=IngresoForm, redirect_authenticated_user=True), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('alertas/', views.alertas, name='alertas'),
    path('simulador/', views.simulador, name='simulador'),
    path('api/niveles/', views.niveles_api, name='niveles_api'),
]
