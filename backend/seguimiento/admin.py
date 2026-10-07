from django.contrib import admin

from .models import ArtistaSeguido, ConciertoGuardado


@admin.register(ArtistaSeguido)
class ArtistaSeguidoAdmin(admin.ModelAdmin):
    list_display = ["artista", "usuario", "creado"]
    list_select_related = ["artista", "usuario"]
    search_fields = ["artista__nombre", "usuario__email"]


@admin.register(ConciertoGuardado)
class ConciertoGuardadoAdmin(admin.ModelAdmin):
    list_display = ["concierto", "usuario", "creado"]
    list_select_related = ["concierto", "usuario"]
    search_fields = ["concierto__titulo", "usuario__email"]
