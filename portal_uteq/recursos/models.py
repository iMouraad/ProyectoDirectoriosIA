# portal_uteq/recursos/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Modelo para representar una Carrera universitaria
class Carrera(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Carrera")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de la Carrera")
    imagen = models.ImageField(upload_to='carreras_imagenes/', null=True, blank=True, verbose_name="Imagen de la Carrera")

    class Meta:
        verbose_name = "Carrera Universitaria"
        verbose_name_plural = "Carreras Universitarias"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# Modelo para representar un Recurso digital
class Recurso(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_APROBADO = 'aprobado'
    ESTADO_RECHAZADO = 'rechazado'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente de Revisión'),
        (ESTADO_APROBADO, 'Aprobado'),
        (ESTADO_RECHAZADO, 'Rechazado'),
    ]

    TIPO_CHOICES = [
        ('app', 'Aplicación'),
        ('herramienta', 'Herramienta Web'),
        ('pagina_web', 'Página Web'),
        ('ia', 'Inteligencia Artificial'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre del Recurso")
    descripcion = models.TextField(verbose_name="Descripción Detallada")
    uso_ideal = models.TextField(blank=True, null=True, verbose_name="Uso Ideal", help_text="Liste los usos ideales del recurso, uno por línea.")
    url_externa = models.URLField(max_length=500, verbose_name="URL Externa")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro', verbose_name="Tipo de Recurso")
    imagen = models.ImageField(upload_to='recursos_imagenes/', null=True, blank=True, verbose_name="Imagen Representativa")
    carreras = models.ManyToManyField(Carrera, related_name='recursos', verbose_name="Carreras Asociadas", blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    sugerido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recursos_sugeridos',
        verbose_name="Sugerido por"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        verbose_name="Estado de Aprobación"
    )

    class Meta:
        verbose_name = "Recurso Digital"
        verbose_name_plural = "Recursos Digitales"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# Modelo para extender la información del usuario
class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    cedula = models.CharField(max_length=10, unique=True, verbose_name="Cédula")
    carrera = models.ForeignKey(Carrera, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Carrera del Estudiante")
    # Nuevo campo para los recursos favoritos
    recursos_favoritos = models.ManyToManyField(
        'Recurso',
        related_name='favorito_de',
        blank=True,
        verbose_name="Recursos Favoritos"
    )
    # Campos de gamificación
    puntos = models.IntegerField(default=0, verbose_name="Puntos de Gamificación")
    racha_actual = models.IntegerField(default=0, verbose_name="Racha de Conexión")
    ultima_conexion_racha = models.DateTimeField(null=True, blank=True, verbose_name="Última Conexión para Racha")

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"Perfil de {self.user.username}"

# Modelo para las valoraciones de los recursos
class Valoracion(models.Model):
    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name='valoraciones')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='valoraciones')
    puntuacion = models.IntegerField(
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
        verbose_name="Puntuación"
    )
    comentario = models.TextField(verbose_name="Comentario")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Valoración"
        verbose_name_plural = "Valoraciones"
        ordering = ['-fecha_creacion']
        # Un usuario solo puede valorar un recurso una vez
        unique_together = ('recurso', 'user')

    def __str__(self):
        return f"Valoración de {self.user.username} para {self.recurso.nombre}"

# --- Modelos para Gamificación (Misiones Diarias) ---

class Mision(models.Model):
    """
    Define los tipos de misiones disponibles en el sistema.
    """
    KEY_CHOICES = [
        ('login_diario', 'Login Diario'),
        ('valorar_recurso', 'Valorar un Recurso'),
        ('sugerir_recurso', 'Sugerir un Recurso'),
        ('visitar_recurso', 'Visitar un Recurso'), # Ejemplo, podría ser más específico
        # ... otros tipos de misiones
    ]
    key = models.CharField(max_length=50, unique=True, choices=KEY_CHOICES, verbose_name="Clave de Misión")
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Misión")
    descripcion = models.TextField(verbose_name="Descripción")
    puntos_recompensa = models.IntegerField(default=10, verbose_name="Puntos de Recompensa")
    activa = models.BooleanField(default=True, verbose_name="Misión Activa")

    class Meta:
        verbose_name = "Misión"
        verbose_name_plural = "Misiones"

    def __str__(self):
        return self.nombre

class MisionDiariaUsuario(models.Model):
    """
    Representa una misión diaria asignada a un usuario para una fecha específica.
    """
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='misiones_diarias')
    mision = models.ForeignKey(Mision, on_delete=models.CASCADE, related_name='asignaciones_diarias')
    fecha_asignacion = models.DateField(default=timezone.now, verbose_name="Fecha de Asignación")
    completada = models.BooleanField(default=False, verbose_name="Completada")
    fecha_completado = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Completado")

    class Meta:
        unique_together = ('perfil', 'mision', 'fecha_asignacion') # Un usuario, una misión, por día
        verbose_name = "Misión Diaria de Usuario"
        verbose_name_plural = "Misiones Diarias de Usuarios"

    def __str__(self):
        return f"{self.perfil.user.username} - {self.mision.nombre} ({'Completada' if self.completada else 'Pendiente'}) el {self.fecha_asignacion}"

class HistorialVisitas(models.Model):
    """
    Registra cada vez que un usuario visita un recurso.
    """
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='historial_visitas')
    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name='visitas')
    fecha_visita = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Visita")

    class Meta:
        ordering = ['-fecha_visita']
        verbose_name = "Historial de Visita"
        verbose_name_plural = "Historiales de Visitas"

    def __str__(self):
        return f"{self.perfil.user.username} visitó {self.recurso.nombre} el {self.fecha_visita}"
