from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from conciertos.models import Artista

from .wikipedia import ErrorWikipedia, Wikipedia

DIAS_ENTRE_REVISIONES = 30


def actualizar_descripcion(artista, wikipedia):
    """Busca y guarda la descripción. Devuelve True si encontró una. Lanza ErrorWikipedia si falla la red."""
    resumen = wikipedia.buscar(artista)
    if resumen:
        artista.descripcion = resumen.texto
        artista.descripcion_fuente = resumen.url
    elif artista.descripcion_fuente:
        # La que había venía de Wikipedia y ya no aplica (p. ej. corregiste el artículo).
        artista.descripcion = artista.descripcion_fuente = ""
    artista.descripcion_revisada = timezone.now()
    artista.save(update_fields=["descripcion", "descripcion_fuente", "descripcion_revisada"])
    return resumen is not None


def pendientes(limite):
    """Los artistas que nunca se han buscado (primero) o hace más de 30 días, salvo los de descripción fija."""
    hace_un_mes = timezone.now() - timedelta(days=DIAS_ENTRE_REVISIONES)
    return (
        Artista.objects.filter(descripcion_fija=False)
        .filter(Q(descripcion_revisada__isnull=True) | Q(descripcion_revisada__lt=hace_un_mes))
        .order_by(F("descripcion_revisada").asc(nulls_first=True), "pk")[:limite]
    )


def actualizar_pendientes(limite=150, wikipedia=None):
    """Devuelve (encontradas, sin_descripcion, errores)."""
    wikipedia = wikipedia or Wikipedia()
    encontradas = sin_descripcion = 0
    errores = []
    for artista in pendientes(limite):
        try:
            if actualizar_descripcion(artista, wikipedia):
                encontradas += 1
            else:
                sin_descripcion += 1
        except ErrorWikipedia as error:
            errores.append(f"{artista.nombre}: {error}")  # queda pendiente para otra noche
    return encontradas, sin_descripcion, errores
