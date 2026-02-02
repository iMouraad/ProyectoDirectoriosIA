from django.apps import AppConfig


class RecursosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal_uteq.recursos'

    def ready(self):
        import portal_uteq.recursos.signals # Importa las señales
