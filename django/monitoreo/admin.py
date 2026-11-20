from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Estanque, Medicion, Alerta

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Rol en el fundo', {'fields': ('rol',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Rol en el fundo', {'fields': ('rol',)}),)

admin.site.register(Estanque)
admin.site.register(Medicion)
admin.site.register(Alerta)
admin.site.site_header = 'Fundo San Carlos · Administración técnica'
