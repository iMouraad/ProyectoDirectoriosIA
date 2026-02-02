from django.views.generic import ListView, TemplateView, CreateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Avg
from datetime import date, datetime
from .models import Carrera, Recurso, Valoracion, Perfil, MisionDiariaUsuario
from .forms import SugerenciaRecursoForm, ValoracionForm, CustomUserCreationForm
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login') # Redirigir a login tras el registro

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('recursos:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user, temporary_password = form.save()
        self.object = user # Manually set self.object as per CreateView's contract
        
        # Enviar correo de bienvenida con la contraseña temporal
        try:
            subject = render_to_string('registration/email_subject.txt').strip()
            body = render_to_string('registration/email_body.txt', {
                'user': user,
                'temporary_password': temporary_password
            })
            
            send_mail(
                subject,
                body,
                'no-reply@uteq.edu.ec', # Remitente
                [user.email],         # Destinatario
                fail_silently=False,
            )
            messages.success(self.request, '¡Registro exitoso! Revisa tu correo electrónico para obtener tu contraseña temporal.')
        except Exception as e:
            # Opcional: registrar el error y notificar al usuario
            print(f"Error al enviar correo de bienvenida: {e}")
            messages.warning(self.request, 'Se creó tu cuenta, pero hubo un error al enviar el correo de bienvenida. Contacta a soporte.')

        return redirect(self.get_success_url())

class GroupRequiredMixin(AccessMixin):
    group_names = []


    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.is_superuser or request.user.groups.filter(name__in=self.group_names).exists():
            return super().dispatch(request, *args, **kwargs)
            
        return self.handle_no_permission()

class SugerenciaRecursoCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    model = Recurso
    form_class = SugerenciaRecursoForm
    template_name = 'recursos/sugerencia_form.html'
    success_url = reverse_lazy('recursos:dashboard')
    group_names = ['Docente', 'Administrador']

    def form_valid(self, form):
        response = super().form_valid(form) # Primero llamamos al form_valid original

        # --- Lógica de Gamificación: Completar misión "Sugerir un Recurso" ---
        from datetime import date, datetime
        user = self.request.user
        if hasattr(user, 'perfil'):
            user_profile = user.perfil
            today_date = date.today()

            sugerir_mision_user = MisionDiariaUsuario.objects.filter(
                perfil=user_profile,
                fecha_asignacion=today_date,
                mision__key='sugerir_recurso',
                completada=False
            ).first()

            if sugerir_mision_user:
                sugerir_mision_user.completada = True
                sugerir_mision_user.fecha_completado = datetime.now()
                sugerir_mision_user.save()
                user_profile.puntos += sugerir_mision_user.mision.puntos_recompensa
                user_profile.save()
        # --- Fin Lógica de Gamificación ---

        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

# La HomeView ahora es un RedirectView
class HomeView(LoginRequiredMixin, RedirectView):
    url = reverse_lazy('recursos:dashboard') # Redirige al Dashboard si está logueado

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'recursos/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['total_carreras'] = Carrera.objects.count()
        context['total_recursos'] = Recurso.objects.filter(estado=Recurso.ESTADO_APROBADO).count()

        # Añadir datos de gamificación para todos los usuarios autenticados
        if user.is_authenticated and hasattr(user, 'perfil'):
            from .models import HistorialVisitas
            context['user_puntos'] = user.perfil.puntos
            context['user_racha'] = user.perfil.racha_actual
            
            # Recuperar misiones diarias del usuario para hoy
            today_date = date.today()
            context['misiones_diarias'] = MisionDiariaUsuario.objects.filter(
                perfil=user.perfil,
                fecha_asignacion=today_date
            ).select_related('mision').order_by('completada', 'mision__nombre')

            # Recuperar historial de visitas (últimos 5 recursos únicos)
            all_visits = HistorialVisitas.objects.filter(
                perfil=user.perfil
            ).select_related('recurso').order_by('-fecha_visita')
            
            unique_visited_recursos = []
            seen_recurso_ids = set()

            for visit in all_visits:
                if visit.recurso.id not in seen_recurso_ids:
                    unique_visited_recursos.append(visit)
                    seen_recurso_ids.add(visit.recurso.id)
                    if len(unique_visited_recursos) >= 5:
                        break
            
            context['historial_visitas'] = unique_visited_recursos

        if user.is_superuser or user.groups.filter(name='Gestor de Contenido').exists():
            context['dashboard_type'] = 'admin_gestor'
            context['recursos_pendientes'] = Recurso.objects.filter(estado=Recurso.ESTADO_PENDIENTE).count()
            context['carreras_con_recursos'] = Carrera.objects.annotate(num_recursos=Count('recursos')).filter(num_recursos__gt=0).order_by('-num_recursos')[:5]

        elif user.groups.filter(name='Docente').exists():
            context['dashboard_type'] = 'docente'
            context['mis_sugerencias_pendientes'] = Recurso.objects.filter(
                sugerido_por=user, 
                estado=Recurso.ESTADO_PENDIENTE
            ).count()
            
            if hasattr(user, 'perfil') and user.perfil.carrera:
                context['recursos_mi_carrera_aprobados'] = Recurso.objects.filter(
                    carreras=user.perfil.carrera,
                    estado=Recurso.ESTADO_APROBADO
                )[:5]

        else: # Estudiantes
            context['dashboard_type'] = 'estudiante'
            if hasattr(user, 'perfil') and user.perfil.carrera:
                context['mi_carrera'] = user.perfil.carrera
                context['recursos_mi_carrera'] = Recurso.objects.filter(
                    carreras=user.perfil.carrera,
                    estado=Recurso.ESTADO_APROBADO
                )[:5]
            
        return context

class CareerListView(LoginRequiredMixin, ListView):
    model = Carrera
    template_name = 'recursos/career_list.html'
    context_object_name = 'carreras'

# Nueva vista para mostrar los tipos de recursos de una carrera
class ResourceTypeListView(LoginRequiredMixin, TemplateView):
    template_name = 'recursos/resource_type_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['carrera'] = Carrera.objects.get(pk=self.kwargs['pk'])

        # Metadata para los tipos de recurso
        tipos_metadata = [
            {
                'key': 'ia',
                'display': 'Inteligencia Artificial',
                'icon': 'bi-robot',
                'description': 'Plataformas y modelos de inteligencia artificial generativa.'
            },
            {
                'key': 'herramienta',
                'display': 'Herramienta Web',
                'icon': 'bi-tools',
                'description': 'Servicios y utilidades que funcionan desde tu navegador.'
            },
            {
                'key': 'app',
                'display': 'Aplicación',
                'icon': 'bi-window-stack',
                'description': 'Software instalable para sistemas de escritorio o móviles.'
            },
            {
                'key': 'pagina_web',
                'display': 'Página Web',
                'icon': 'bi-globe',
                'description': 'Sitios informativos, portafolios o referencias de interés.'
            }
        ]
        
        context['tipos_de_recurso'] = tipos_metadata
        return context

from django.db.models import Q, Avg, Value
from django.db.models.functions import Coalesce

# ... (el resto de las importaciones se mantienen igual)
# ... (el resto de las vistas se mantienen igual hasta ResourceListView)

# Vista modificada para listar los recursos filtrados por tipo, con búsqueda y ordenamiento
class ResourceListView(LoginRequiredMixin, ListView):
    model = Recurso
    template_name = 'recursos/resource_list.html'
    context_object_name = 'recursos'
    paginate_by = 9 # Opcional: para paginar los resultados

    def get_queryset(self):
        # Parámetros de la URL
        query = self.request.GET.get('q')
        sort_by = self.request.GET.get('sort', 'recientes')

        # 1. Anotación base para la calificación promedio
        # Se anota siempre para que el dato esté disponible en la plantilla
        queryset = Recurso.objects.filter(
            carreras__id=self.kwargs['pk'],
            tipo=self.kwargs['tipo'],
            estado=Recurso.ESTADO_APROBADO
        ).annotate(
            avg_rating=Coalesce(Avg('valoraciones__puntuacion'), Value(0.0))
        )

        # 2. Lógica de Búsqueda
        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query) | Q(descripcion__icontains=query)
            )

        # 3. Lógica de Ordenamiento
        if sort_by == 'valorados':
            # Ordena por la anotación y luego por fecha como desempate
            queryset = queryset.order_by('-avg_rating', '-fecha_creacion')
        else: # 'recientes' o cualquier otro valor
            queryset = queryset.order_by('-fecha_creacion')

        return queryset.distinct()
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos la carrera y el tipo de recurso para usarlos en el template
        context['carrera'] = Carrera.objects.get(pk=self.kwargs['pk'])
        context['tipo'] = self.kwargs['tipo']
        context['tipo_display'] = dict(Recurso.TIPO_CHOICES).get(self.kwargs['tipo'])
        
        # Pasamos los parámetros de búsqueda al contexto para mantener su estado en el template
        context['q'] = self.request.GET.get('q', '')
        context['sort'] = self.request.GET.get('sort', 'recientes')
        
        # Añadimos los IDs de los recursos favoritos del usuario para la lógica del frontend
        if self.request.user.is_authenticated and hasattr(self.request.user, 'perfil'):
            context['favorite_resource_ids'] = list(self.request.user.perfil.recursos_favoritos.values_list('id', flat=True))
        else:
            context['favorite_resource_ids'] = []
            
        return context

# Vista de detalle del recurso con comentarios y formulario
class ResourceDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Recurso
    template_name = 'recursos/resource_detail.html'
    context_object_name = 'recurso'
    form_class = ValoracionForm

    def get_success_url(self):
        return reverse('recursos:resource_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recurso = self.get_object()

        # --- Lógica de Gamificación: Completar misión "Visitar un Recurso" ---
        if self.request.user.is_authenticated and hasattr(self.request.user, 'perfil'):
            from django.utils import timezone
            user_profile = self.request.user.perfil
            today_date = date.today()

            visitar_mision_user = MisionDiariaUsuario.objects.filter(
                perfil=user_profile,
                fecha_asignacion=today_date,
                mision__key='visitar_recurso',
                completada=False
            ).first()

            if visitar_mision_user:
                visitar_mision_user.completada = True
                visitar_mision_user.fecha_completado = timezone.now()
                visitar_mision_user.save()
                user_profile.puntos += visitar_mision_user.mision.puntos_recompensa
                user_profile.save()
        # --- Fin Lógica de Gamificación ---
        
        # Obtenemos valoraciones y calculamos el promedio
        valoraciones = recurso.valoraciones.all()
        context['valoraciones'] = valoraciones
        context['average_rating'] = valoraciones.aggregate(Avg('puntuacion'))['puntuacion__avg']

        # Comprobamos si el usuario ya ha valorado este recurso
        user_has_commented = False
        if self.request.user.is_authenticated:
            user_has_commented = valoraciones.filter(user=self.request.user).exists()
        
        context['user_has_commented'] = user_has_commented
        
        # Lógica para verificar si el recurso es favorito para el usuario actual
        if self.request.user.is_authenticated and hasattr(self.request.user, 'perfil'):
            context['is_favorited'] = self.request.user.perfil.recursos_favoritos.filter(pk=recurso.pk).exists()
        else:
            context['is_favorited'] = False

        # Añadimos el formulario al contexto si el usuario no ha comentado
        if not user_has_commented:
            context['form'] = self.get_form()
            
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        self.object = self.get_object()
        form = self.get_form()
        
        # Verificamos si el usuario ya comentó para evitar POSTs maliciosos
        if self.object.valoraciones.filter(user=request.user).exists():
            # Aquí se podría añadir un mensaje con django.contrib.messages
            return self.form_invalid(form)
            
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        valoracion = form.save(commit=False)
        valoracion.recurso = self.object
        valoracion.user = self.request.user
        valoracion.save()
        return super().form_valid(form)

@login_required
@require_POST
def agregar_valoracion_ajax(request, pk):
    recurso = get_object_or_404(Recurso, pk=pk)

    if Valoracion.objects.filter(recurso=recurso, user=request.user).exists():
        return JsonResponse({'status': 'error', 'message': 'Ya has valorado este recurso.'}, status=400)

    form = ValoracionForm(request.POST)

    if form.is_valid():
        valoracion = form.save(commit=False)
        valoracion.recurso = recurso
        valoracion.user = request.user
        valoracion.save()

        # --- Lógica de Gamificación: Completar misión "Valorar un Recurso" ---
        user_profile = request.user.perfil
        today_date = date.today()

        valorar_mision_user = MisionDiariaUsuario.objects.filter(
            perfil=user_profile,
            fecha_asignacion=today_date,
            mision__key='valorar_recurso',
            completada=False
        ).first()

        if valorar_mision_user:
            valorar_mision_user.completada = True
            valorar_mision_user.fecha_completado = datetime.now()
            valorar_mision_user.save()
            user_profile.puntos += valorar_mision_user.mision.puntos_recompensa
            user_profile.save()
        # --- Fin Lógica de Gamificación ---

        # Después de guardar, recalculamos las estadísticas
        stats = recurso.valoraciones.aggregate(
            new_avg_rating=Avg('puntuacion'),
            new_rating_count=Count('id')
        )

        data = {
            'status': 'success',
            'user': f"{valoracion.user.first_name} {valoracion.user.last_name}" if valoracion.user.first_name else valoracion.user.username,
            'puntuacion': valoracion.puntuacion,
            'comentario': valoracion.comentario,
            'fecha_creacion': valoracion.fecha_creacion.strftime('%d de %B de %Y a las %H:%M'),
            'new_avg_rating': round(stats['new_avg_rating'], 1) if stats['new_avg_rating'] else 0,
            'new_rating_count': stats['new_rating_count'],
        }
        return JsonResponse(data)
    else:
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

class FavoriteResourceListView(LoginRequiredMixin, ListView):
    model = Recurso
    template_name = 'recursos/favorite_resources_list.html'
    context_object_name = 'recursos_favoritos'
    paginate_by = 9 # Opcional: para paginar los resultados

    def get_queryset(self):
        # Asegurarse de que el usuario tenga un perfil antes de intentar acceder a los favoritos
        if hasattr(self.request.user, 'perfil'):
            # Devolver los recursos favoritos del perfil del usuario actual
            return self.request.user.perfil.recursos_favoritos.all().order_by('-fecha_creacion')
        return Recurso.objects.none() # Si no hay perfil, devolver un queryset vacío

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Mis Recursos Favoritos'
        return context


@login_required
@require_POST
def marcar_visita_recurso_ajax(request, pk):
    """
    Marca la misión 'visitar_recurso' como completada y registra la visita
    en el historial del usuario.
    """
    recurso = get_object_or_404(Recurso, pk=pk)
    if hasattr(request.user, 'perfil'):
        user_profile = request.user.perfil
        
        # --- Registrar en el historial de visitas ---
        from .models import HistorialVisitas
        HistorialVisitas.objects.create(perfil=user_profile, recurso=recurso)
        
        # --- Lógica de Gamificación ---
        today_date = date.today()

        visitar_mision_user = MisionDiariaUsuario.objects.filter(
            perfil=user_profile,
            fecha_asignacion=today_date,
            mision__key='visitar_recurso',
            completada=False
        ).first()

        if visitar_mision_user:
            visitar_mision_user.completada = True
            visitar_mision_user.fecha_completado = datetime.now()
            visitar_mision_user.save()
            user_profile.puntos += visitar_mision_user.mision.puntos_recompensa
            user_profile.save()
            return JsonResponse({'status': 'success', 'message': 'Misión completada y visita registrada.'})

    return JsonResponse({'status': 'success', 'message': 'Visita registrada.'})


@login_required
@require_POST
def toggle_favorite_resource(request, pk):
    recurso = get_object_or_404(Recurso, pk=pk)

    if not hasattr(request.user, 'perfil'):
        return JsonResponse({'status': 'error', 'message': 'El usuario no tiene un perfil asociado.'}, status=400)

    user_profile = request.user.perfil

    if recurso in user_profile.recursos_favoritos.all():
        user_profile.recursos_favoritos.remove(recurso)
        is_favorited = False
        message = 'Recurso eliminado de favoritos.'
    else:
        user_profile.recursos_favoritos.add(recurso)
        is_favorited = True
        message = 'Recurso añadido a favoritos.'

    return JsonResponse({
        'status': 'success',
        'is_favorited': is_favorited,
        'message': message
    })

from django.http import HttpResponse
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def debug_log_view(request):
    """
    Una vista temporal para depuración en producción.
    Muestra el contenido del archivo de log.
    ¡¡¡ELIMINAR DESPUÉS DE LA DEPURACIÓN!!!
    """
    log_file_path = settings.BASE_DIR / 'django_errors.log'
    try:
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        return HttpResponse(log_content, content_type='text/plain; charset=utf-8')
    except FileNotFoundError:
        return HttpResponse("El archivo de log 'django_errors.log' no se ha creado todavía. Provoca el error 500 primero.", content_type='text/plain; charset=utf-8')
    except Exception as e:
        return HttpResponse(f"Error al leer el archivo de log: {e}", content_type='text/plain; charset=utf-8')
