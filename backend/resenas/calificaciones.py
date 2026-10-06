"""Promedios de reseñas por artista y por recinto. Solo cuentan las visibles."""
from django.db.models import Avg, Count, OuterRef, Subquery
from django.db.models.functions import Coalesce

from .models import Resena


def redondear(valor):
    return round(valor, 1) if valor is not None else None


def calificacion_artista(artista):
    """Promedio general y por aspecto de todas las reseñas de los conciertos del artista."""
    datos = Resena.objects.visibles().filter(concierto__artista=artista).aggregate(
        promedio=Avg("general"), total=Count("id"),
        show=Avg("show"), sonido=Avg("sonido"), puntualidad=Avg("puntualidad"),
    )
    return {clave: valor if clave == "total" else redondear(valor) for clave, valor in datos.items()}


def calificacion_recinto(recinto):
    """Promedio de la calificación "el recinto"; total = cuántas reseñas lo calificaron."""
    datos = Resena.objects.visibles().filter(concierto__recinto=recinto, recinto__isnull=False).aggregate(
        promedio=Avg("recinto"), total=Count("id")
    )
    return {"promedio": redondear(datos["promedio"]), "total": datos["total"]}


def anotar_calificacion_artista(conciertos):
    """Agrega promedio_artista y resenas_artista a cada concierto en la misma consulta (sin N+1)."""
    del_artista = (
        Resena.objects.visibles()
        .filter(concierto__artista=OuterRef("artista"))
        .order_by()
        .values("concierto__artista")  # agrupa por artista
    )
    return conciertos.annotate(
        promedio_artista=Subquery(del_artista.annotate(v=Avg("general")).values("v")),
        resenas_artista=Coalesce(Subquery(del_artista.annotate(v=Count("id")).values("v")), 0),
    )
