# portal_uteq/recursos/forms.py
from django import forms
from django.contrib.auth.models import User
import unidecode
from .models import Recurso, Carrera, Valoracion, Perfil # Importamos Recurso, Carrera, Valoracion y Perfil para los formularios

from django.db import transaction
import random

class CustomUserCreationForm(forms.ModelForm):
    cedula = forms.CharField(max_length=10, label="Cédula", help_text="Tu número de cédula de 10 dígitos.")
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.all(),
        label="Carrera",
        empty_label="Selecciona tu carrera",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "cedula", "carrera")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Opcional: aplicar clases de Bootstrap si no se hace en el template
        self.fields['first_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Tus nombres'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Tus apellidos'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'tu.email@institucional.com'})
        self.fields['cedula'].widget.attrs.update({'class': 'form-control', 'placeholder': '1234567890'})

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if Perfil.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya ha sido registrada.")
        return cedula

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)

        # --- Lógica de generación de username (Formato solicitado) ---
        first_name = self.cleaned_data.get('first_name', '')
        last_name = self.cleaned_data.get('last_name', '')
        email = self.cleaned_data.get('email', '') 

        username = ""
        if first_name and last_name:
            # Normalizar nombres para la generación del username
            normalized_first_name = unidecode.unidecode(first_name.lower())
            # Separar el apellido en partes (considerando posibles dobles apellidos)
            normalized_last_name_parts = unidecode.unidecode(last_name.lower()).split()

            if normalized_first_name and normalized_last_name_parts:
                first_letter_first_name = normalized_first_name[0]
                first_last_name_part = normalized_last_name_parts[0]
                
                if len(normalized_last_name_parts) > 1:
                    # Si hay un segundo apellido, tomar su primera letra
                    second_last_name_first_letter = normalized_last_name_parts[1][0]
                    username = f"{first_letter_first_name}{first_last_name_part}{second_last_name_first_letter}"
                else:
                    # Si solo hay un apellido
                    username = f"{first_letter_first_name}{first_last_name_part}"
            else:
                # Fallback si los nombres no se formaron correctamente después de la normalización
                if email:
                    username = email.split('@')[0]
                elif normalized_first_name: # Solo el primer nombre
                    username = normalized_first_name
                else: # Generic fallback
                    username = f"user_{User.objects.count()}"
        elif email: # Fallback al email si los nombres no son suficientes
            username = email.split('@')[0]
        else: # Fallback definitivo
            username = f"user_{User.objects.count()}"

        # Asegurarse de que el username no esté vacío (debería estar cubierto por la lógica, pero como salvaguarda)
        if not username:
             username = f"user_{User.objects.count()}"

        # Nos aseguramos de que el username sea único
        counter = 1
        base_username = username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username


        # --- Lógica de generación de contraseña temporal ---
        cedula = self.cleaned_data.get('cedula')
        random_suffix = random.randint(1000, 9999)
        temporary_password = f"{cedula}*{random_suffix}"
        user.set_password(temporary_password)

        if commit:
            user.save()
            Perfil.objects.create(
                user=user,
                cedula=cedula,
                carrera=self.cleaned_data.get('carrera')
            )
        return user, temporary_password


class SugerenciaRecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        # Añadimos 'imagen' y 'uso_ideal' a los campos que el docente rellenará
        fields = ['nombre', 'descripcion', 'uso_ideal', 'url_externa', 'tipo', 'carreras', 'imagen']
        labels = {
            'nombre': 'Nombre del Recurso/IA',
            'descripcion': 'Descripción Detallada',
            'uso_ideal': 'Uso Ideal (un uso por línea)',
            'url_externa': 'Enlace (URL) del Recurso',
            'tipo': 'Tipo de Recurso',
            'carreras': 'Carreras a las que aplica este recurso',
            'imagen': 'Imagen o Logo Representativo',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'uso_ideal': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ejemplo:\nInvestigar y resumir PDFs\nRedacción y gramática\nGeneración de código'}),
            'carreras': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Aplicamos estilos de Bootstrap
            if field_name != 'carreras':
                field.widget.attrs['class'] = 'form-control'
            if field_name == 'tipo':
                field.widget.attrs['class'] += ' form-select'
        
        # Si el usuario NO es admin y tiene una carrera, limitamos el campo 'carreras'
        if user and not user.is_superuser and hasattr(user, 'perfil') and user.perfil.carrera:
            self.fields['carreras'].queryset = Carrera.objects.filter(pk=user.perfil.carrera.pk)
            self.fields['carreras'].initial = [user.perfil.carrera.pk]
            self.fields['carreras'].empty_label = None # No mostrar opción en blanco

class ValoracionForm(forms.ModelForm):
    puntuacion = forms.ChoiceField(
        choices=[(5, '5 Estrellas'), (4, '4 Estrellas'), (3, '3 Estrellas'), (2, '2 Estrellas'), (1, '1 Estrella')],
        widget=forms.RadioSelect,
        label="Tu Puntuación",
        required=True
    )

    class Meta:
        model = Valoracion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Escribe tu reseña aquí...'}),
        }
        labels = {
            'comentario': 'Tu Comentario',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicamos estilos de Bootstrap
        self.fields['puntuacion'].widget.attrs['class'] = 'form-check-input'
        self.fields['comentario'].widget.attrs['class'] = 'form-control'