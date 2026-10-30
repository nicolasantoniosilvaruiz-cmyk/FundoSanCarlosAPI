import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = 'administrador', 'Administrador'
        TRABAJADOR = 'trabajador', 'Trabajador'

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.TRABAJADOR)

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR


class Estanque(models.Model):
    class Tipo(models.TextChoices):
        AGUA = 'agua', 'Agua'
        PETROLEO = 'petroleo', 'Petróleo diésel'

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, unique=True)
    capacidad_litros = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    umbral_pct = models.DecimalField(max_digits=5, decimal_places=2, default=30, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        ordering = ['tipo']
        constraints = [
            models.CheckConstraint(condition=models.Q(capacidad_litros__gt=0), name='capacidad_positiva'),
            models.CheckConstraint(condition=models.Q(umbral_pct__gte=0, umbral_pct__lte=100), name='umbral_valido'),
        ]

    def __str__(self):
        return self.nombre


class Medicion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estanque = models.ForeignKey(Estanque, on_delete=models.PROTECT, related_name='mediciones')
    volumen_litros = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    simulada = models.BooleanField(default=True)
    creada_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        constraints = [models.CheckConstraint(condition=models.Q(volumen_litros__gte=0), name='volumen_no_negativo')]

    @property
    def porcentaje(self):
        return self.volumen_litros / self.estanque.capacidad_litros * 100


class Alerta(models.Model):
    estanque = models.ForeignKey(Estanque, on_delete=models.PROTECT)
    medicion = models.ForeignKey(Medicion, on_delete=models.PROTECT)
    umbral_aplicado = models.DecimalField(max_digits=5, decimal_places=2)
    creada = models.DateTimeField(auto_now_add=True)
    resuelta = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creada']
