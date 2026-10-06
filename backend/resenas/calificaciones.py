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


def distribucion(resenas):
    """Cuántas reseñas dieron 5, 4, 3, 2 y 1 estrellas: [{"estrellas": 5, "total": 12}, ...]."""
    conteo = dict(resenas.values_list("general").annotate(n=Count("id")).order_by())
    return [{"estrellas": n, "total": conteo.get(n, 0)} for n in (5, 4, 3, 2, 1)]


def por_ciudad(artista):
    """Promedio general del artista en cada ciudad donde lo han reseñado, la mejor primero."""
    filas = (
        Resena.objects.visibles().filter(concierto__artista=artista)
        .values("concierto__recinto__ciudad__nombre", "concierto__recinto__ciudad__slug")
        .annotate(promedio=Avg("general"), total=Count("id"))
        .order_by("-promedio", "-total")
    )
    return [
        {
            "ciudad": f["concierto__recinto__ciudad__nombre"], "slug": f["concierto__recinto__ciudad__slug"],
            "promedio": redondear(f["promedio"]), "total": f["total"],
        }
        for f in filas
    ]
