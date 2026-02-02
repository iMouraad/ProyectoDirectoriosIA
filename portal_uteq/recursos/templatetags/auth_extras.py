from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='in_group')
def in_group(user, group_name):
    """
    Verifica si un usuario pertenece a un grupo específico.
    Uso en la plantilla: {% if user|in_group:"NombreDelGrupo" %}
    """
    try:
        group = Group.objects.get(name=group_name)
        return group in user.groups.all()
    except Group.DoesNotExist:
        return False
