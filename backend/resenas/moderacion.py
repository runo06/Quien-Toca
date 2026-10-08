"""Moderación de reportes: la usan el panel de Django y la sección de editores de la página."""
from django.utils import timezone

from .models import Reporte, Resena


def aceptar(reportes):
    """Oculta las reseñas reportadas y resuelve todos sus reportes pendientes.

    Devuelve (reseñas ocultas, reportes resueltos).
    """
    ids = set(reportes.values_list("resena_id", flat=True))  # se leen ya: el filtro de pendientes cambia
    Resena.objects.filter(pk__in=ids).update(oculta=True)
    resueltos = Reporte.objects.filter(resena__in=ids, estado=Reporte.Estado.PENDIENTE).update(
        estado=Reporte.Estado.ACEPTADO, revisado=timezone.now()
    )
    return len(ids), resueltos


def descartar(reportes):
    """La reseña está bien: solo se cierran estos reportes. Devuelve cuántos."""
    return reportes.update(estado=Reporte.Estado.DESCARTADO, revisado=timezone.now())
