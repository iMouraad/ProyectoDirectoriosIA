# portal_uteq/recursos/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from datetime import date, timedelta
from django.utils import timezone
from .models import Perfil, Mision, MisionDiariaUsuario
import random

from django.db import transaction

@receiver(user_logged_in)
def update_streak_and_assign_missions(sender, request, user, **kwargs):
    if hasattr(user, 'perfil'):
        with transaction.atomic():
            profile = Perfil.objects.select_for_update().get(pk=user.perfil.pk)
            current_datetime = timezone.now() # Usar timezone.now() de Django
            current_date = current_datetime.date()

            # --- Lógica de Racha Temporal por Minutos ---
            if profile.ultima_conexion_racha:
                time_difference = current_datetime - profile.ultima_conexion_racha
                
                if timedelta(seconds=0) < time_difference <= timedelta(minutes=5):
                    profile.racha_actual += 1
                elif time_difference > timedelta(minutes=5):
                    profile.racha_actual = 1
            else:
                profile.racha_actual = 1
            
            profile.ultima_conexion_racha = current_datetime
            
            # --- Lógica de Asignación de Misiones Diarias ---
            login_mission = Mision.objects.filter(key='login_diario', activa=True).first()

            if not MisionDiariaUsuario.objects.filter(perfil=profile, fecha_asignacion=current_date).exists():
                assigned_missions_keys = set()

                if login_mission:
                    MisionDiariaUsuario.objects.get_or_create(
                        perfil=profile,
                        mision=login_mission,
                        fecha_asignacion=current_date,
                        defaults={'completada': False}
                    )
                    assigned_missions_keys.add(login_mission.key)

                available_missions_for_random = list(Mision.objects.filter(activa=True).exclude(key__in=assigned_missions_keys))
                num_additional_missions = 2 - len(assigned_missions_keys)
                
                if num_additional_missions > 0 and available_missions_for_random:
                    missions_for_today_random = random.sample(available_missions_for_random, min(num_additional_missions, len(available_missions_for_random)))
                    for mision_obj in missions_for_today_random:
                        MisionDiariaUsuario.objects.get_or_create(
                            perfil=profile,
                            mision=mision_obj,
                            fecha_asignacion=current_date,
                            defaults={'completada': False}
                        )
            
            # --- Marcar la misión de "Login Diario" como completada y otorgar puntos ---
            daily_login_mission_user = MisionDiariaUsuario.objects.filter(
                perfil=profile,
                fecha_asignacion=current_date,
                mision__key='login_diario',
                completada=False
            ).first()

            if daily_login_mission_user:
                daily_login_mission_user.completada = True
                daily_login_mission_user.fecha_completado = current_datetime
                daily_login_mission_user.save()
                profile.puntos += daily_login_mission_user.mision.puntos_recompensa
            
            profile.save()