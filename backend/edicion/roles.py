"""El rol "Editor": captura y edita conciertos, aprueba sugerencias y modera reseñas
desde la página. Se da en el panel agregando a la persona al grupo "Editores"."""
from rest_framework import permissions

GRUPO_EDITORES = "Editores"


def es_editor(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.is_superuser or usuario.groups.filter(name=GRUPO_EDITORES).exists()


class EsEditor(permissions.BasePermission):
    message = "Esta sección es solo para editores."

    def has_permission(self, request, view):
        return es_editor(request.user)
