from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Carrera, Recurso, Perfil, Valoracion, Mision, MisionDiariaUsuario
from .forms import CustomUserCreationForm

# Define un 'inline' para el modelo Perfil
class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = 'Perfiles'

# Define una nueva clase UserAdmin
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    
    # Sincronizamos los campos a mostrar con los del nuevo formulario
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'password', 'password2'),
        }),
    )

    inlines = (PerfilInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    readonly_fields = ('username',)

# Re-registra el UserAdmin de Django
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'estado', 'sugerido_por', 'fecha_actualizacion')
    list_filter = ('carreras', 'tipo', 'estado') # Cambiado de 'carrera' a 'carreras'
    search_fields = ('nombre', 'descripcion')
    date_hierarchy = 'fecha_actualizacion'
    ordering = ('-fecha_actualizacion',)
    readonly_fields = ('sugerido_por',)
    
    # Usamos filter_horizontal para una mejor UI con ManyToMany
    filter_horizontal = ('carreras',)

    fieldsets = (
        (None, {
            'fields': ('nombre', 'tipo', 'carreras')
        }),
        ('Detalles del Recurso', {
            'fields': ('descripcion', 'uso_ideal', 'url_externa', 'imagen') # Añadido 'imagen'
        }),
        ('Estado de Publicación', {
            'fields': ('estado', 'sugerido_por')
        }),
    )

@admin.register(Valoracion)
class ValoracionAdmin(admin.ModelAdmin):
    list_display = ('recurso', 'user', 'puntuacion', 'fecha_creacion')
    list_filter = ('puntuacion', 'fecha_creacion')
    search_fields = ('recurso__nombre', 'user__username', 'comentario')
    readonly_fields = ('recurso', 'user', 'puntuacion', 'comentario', 'fecha_creacion')

    def has_add_permission(self, request):
        # Nadie puede añadir valoraciones desde el admin, solo ver/borrar
        return False

    def has_change_permission(self, request, obj=None):
        # Nadie puede cambiar valoraciones desde el admin
        return False

@admin.register(Mision)
class MisionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'key', 'puntos_recompensa', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre', 'descripcion', 'key')
    
@admin.register(MisionDiariaUsuario)
class MisionDiariaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('perfil', 'mision', 'fecha_asignacion', 'completada', 'fecha_completado')
    list_filter = ('mision', 'fecha_asignacion', 'completada')
    search_fields = ('perfil__user__username', 'mision__nombre')
    readonly_fields = ('perfil', 'mision', 'fecha_asignacion', 'completada', 'fecha_completado')

    def has_add_permission(self, request):
        return False

