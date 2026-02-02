# portal_uteq/recursos/urls.py
from django.urls import path
from . import views

app_name = 'recursos' # Esto ayuda a organizar las URLs por aplicación

urlpatterns = [
    # URL para la página de inicio
    path('', views.HomeView.as_view(), name='home'),
    
    # URL para el Registro de Usuarios
    path('register/', views.RegisterView.as_view(), name='register'),

    # URL para el Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # URL para el formulario de sugerencias de recursos
    path('recurso/sugerir/', views.SugerenciaRecursoCreateView.as_view(), name='sugerir_recurso'),

    # URL para ver la lista de todas las carreras
    path('carreras/', views.CareerListView.as_view(), name='career_list'),
    
    # URL para ver los tipos de recursos de una carrera
    path('carreras/<int:pk>/recursos/', views.ResourceTypeListView.as_view(), name='resource_type_list'),

    # URL para ver los recursos de una carrera filtrados por tipo
    path('carreras/<int:pk>/recursos/<str:tipo>/', views.ResourceListView.as_view(), name='resource_list_by_type'),

    # URL para la nueva vista de detalle de un recurso
    path('recurso/<int:pk>/', views.ResourceDetailView.as_view(), name='resource_detail'),

    # URL para añadir valoraciones (comentarios) vía AJAX
    path('recurso/<int:pk>/valorar/', views.agregar_valoracion_ajax, name='agregar_valoracion_ajax'),
    # URL para añadir/quitar un recurso de favoritos via AJAX
    path('recurso/<int:pk>/toggle_favorite/', views.toggle_favorite_resource, name='toggle_favorite_resource'),
    # URL para ver la lista de recursos favoritos del usuario
    path('mis-favoritos/', views.FavoriteResourceListView.as_view(), name='favorite_resources_list'),
    # URL para marcar una visita a un recurso (para misiones)
    path('recurso/<int:pk>/marcar-visita/', views.marcar_visita_recurso_ajax, name='marcar_visita_recurso'),

    # URL TEMPORAL PARA DEPURACION - ¡ELIMINAR DESPUES DE USAR!
    path('debug-log-view-secret-admin-only-12345/', views.debug_log_view, name='debug_log_view'),
]