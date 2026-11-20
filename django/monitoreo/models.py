import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.functions import Round


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = 'administrador', 'Administrador'
        TRABAJADOR = 'trabajador', 'Trabajador'

    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
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
    capacidad_visual_litros = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(Decimal('0.001'))])
    umbral_pct = models.DecimalField(max_digits=5, decimal_places=2, default=30, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        ordering = ['tipo']
        constraints = [
            models.CheckConstraint(condition=models.Q(capacidad_litros__gt=0), name='capacidad_positiva'),
            models.CheckConstraint(condition=models.Q(capacidad_visual_litros__isnull=True) | models.Q(capacidad_visual_litros__gt=0), name='capacidad_visual_positiva'),
            models.CheckConstraint(condition=models.Q(umbral_pct__gte=0, umbral_pct__lte=100), name='umbral_valido'),
        ]

    @property
    def capacidad_representada(self):
        if self.tipo == self.Tipo.AGUA and self.capacidad_visual_litros is not None:
            return self.capacidad_visual_litros
        return self.capacidad_litros

    @property
    def unidad_volumen(self):
        return 'mL' if self.tipo == self.Tipo.AGUA and self.capacidad_representada <= 1 else 'L'

    def volumen_visible(self, litros):
        representado = litros * self.capacidad_representada / self.capacidad_litros
        return representado * 1000 if self.unidad_volumen == 'mL' else representado

    def __str__(self):
        return self.nombre


class Medicion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estanque = models.ForeignKey(Estanque, on_delete=models.PROTECT, related_name='mediciones')
    volumen_litros = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    tomada_en = models.DateTimeField(null=True, blank=True, db_index=True)
    dispositivo = models.ForeignKey('DispositivoAgua', on_delete=models.PROTECT, null=True, blank=True)
    simulada = models.BooleanField(default=True)
    creada_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        constraints = [models.CheckConstraint(condition=models.Q(volumen_litros__gte=0), name='volumen_no_negativo')]

    @property
    def fecha_lectura(self):
        return self.tomada_en or self.fecha

    @property
    def porcentaje(self):
        return self.volumen_litros / self.estanque.capacidad_litros * 100


class Alerta(models.Model):
    estanque = models.ForeignKey(Estanque, on_delete=models.PROTECT)
    medicion = models.ForeignKey(Medicion, on_delete=models.PROTECT)
    umbral_aplicado = models.DecimalField(max_digits=5, decimal_places=2)
    creada = models.DateTimeField(auto_now_add=True)
    resuelta = models.DateTimeField(null=True, blank=True)
    push_evaluada_en = models.DateTimeField(null=True, blank=True)
    push_aceptadas = models.PositiveIntegerField(default=0)
    fcm_evaluada_en = models.DateTimeField(null=True, blank=True)
    fcm_aceptadas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-creada']


class DispositivoAgua(models.Model):
    codigo = models.SlugField(unique=True, max_length=50)
    estanque = models.ForeignKey(Estanque, on_delete=models.PROTECT)
    token_hash = models.CharField(max_length=64, editable=False)
    activo = models.BooleanField(default=True)
    simulador = models.BooleanField(default=True)

    def __str__(self):
        return self.codigo


class SuscripcionPush(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    origen = models.URLField(max_length=255, blank=True, default='')
    endpoint_hash = models.CharField(max_length=64, unique=True)
    endpoint = models.URLField(max_length=2048)
    p256dh = models.CharField(max_length=90)
    auth = models.CharField(max_length=24)
    creada_en = models.DateTimeField(auto_now_add=True)


class SesionMovil(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    huella_usuario = models.CharField(max_length=64, editable=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(db_index=True)
    fcm_token = models.TextField(blank=True, editable=False)
    fcm_hash = models.CharField(max_length=64, null=True, unique=True, editable=False)



class SaldoPetroleo(models.Model):
    estanque = models.OneToOneField(Estanque, on_delete=models.PROTECT)
    litros = models.DecimalField(max_digits=12, decimal_places=3)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(litros__gte=0), name='saldo_petroleo_no_negativo'),
        ]


class MovimientoPetroleo(models.Model):
    solicitud = models.UUIDField(unique=True)
    saldo = models.ForeignKey(SaldoPetroleo, on_delete=models.PROTECT, related_name='movimientos')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    identidad = models.CharField(max_length=310)
    rut_responsable = models.CharField(max_length=12, blank=True)
    saldo_registrado = models.DecimalField(max_digits=12, decimal_places=3)
    tipo = models.CharField(max_length=10, choices=[('retiro', 'Retiro'), ('recarga', 'Recarga')])
    antes = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    despues = models.DecimalField(max_digits=12, decimal_places=3)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(antes__gte=0, cantidad__gt=0, despues__gte=0), name='movimiento_volumen_valido'),
            models.CheckConstraint(condition=(
                models.Q(tipo='retiro', despues=Round(models.F('antes') - models.F('cantidad'), 3))
                | models.Q(tipo='recarga', despues=Round(models.F('antes') + models.F('cantidad'), 3))
            ), name='movimiento_balance_valido'),
        ]
