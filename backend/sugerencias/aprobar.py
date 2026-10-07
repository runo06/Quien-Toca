from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from conciertos.models import Artista, Concierto, Recinto

from .models import Sugerencia


@transaction.atomic
def aprobar(sugerencia):
    """Crea el concierto de la sugerencia (o la liga al que ya existe) y la marca aprobada.

    Reusa el artista y el recinto si ya están (sin importar mayúsculas ni acentos), para
    no duplicar "Café Tacvba" y "cafe tacvba". Devuelve el concierto.
    """
    if sugerencia.estado == Sugerencia.Estado.APROBADA and sugerencia.concierto:
        return sugerencia.concierto

    artista = (
        Artista.objects.filter(nombre__unaccent__iexact=sugerencia.artista.strip()).first()
        or Artista.objects.create(nombre=sugerencia.artista.strip())
    )
    recinto = (
        Recinto.objects.filter(ciudad=sugerencia.ciudad, nombre__unaccent__iexact=sugerencia.recinto.strip()).first()
        or Recinto.objects.create(nombre=sugerencia.recinto.strip(), ciudad=sugerencia.ciudad)
    )
    # ¿Ya lo tenemos (p. ej. llegó de Ticketmaster después de la sugerencia)? Entonces no se duplica.
    concierto = Concierto.objects.filter(
        artista=artista, recinto__ciudad=sugerencia.ciudad, fecha_hora__date=sugerencia.fecha
    ).first()
    if concierto is None:
        zona = ZoneInfo(settings.TIME_ZONE)
        concierto = Concierto.objects.create(
            titulo=artista.nombre,
            artista=artista,
            recinto=recinto,
            fecha_hora=datetime.combine(sugerencia.fecha, sugerencia.hora or time(0), tzinfo=zona),
            hora_por_confirmar=sugerencia.hora is None,
            url_boletos=sugerencia.url_boletos,
            origen=Concierto.Origen.MANUAL,
        )

    sugerencia.estado = Sugerencia.Estado.APROBADA
    sugerencia.concierto = concierto
    sugerencia.revisada = timezone.now()
    sugerencia.save(update_fields=["estado", "concierto", "revisada"])
    return concierto


def rechazar(sugerencia, motivo=""):
    sugerencia.estado = Sugerencia.Estado.RECHAZADA
    sugerencia.motivo_rechazo = motivo or sugerencia.motivo_rechazo
    sugerencia.revisada = timezone.now()
    sugerencia.save(update_fields=["estado", "motivo_rechazo", "revisada"])
