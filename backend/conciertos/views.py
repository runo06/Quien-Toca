from datetime import date

from django.db.models import Count, F, Q
from django.http import JsonResponse
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from resenas.calificaciones import anotar_calificacion_artista

from .models import Artista, Ciudad, Concierto, Recinto, inicio_de_hoy
from .serializers import (
    ArtistaDetalleSerializer,
    CiudadSerializer,
    ConciertoDetalleSerializer,
    ConciertoListaSerializer,
    RecintoDetalleSerializer,
    RecintoEnListaSerializer,
)


def salud(request):
    """GET /api/salud/: responde sin tocar la base. Render la usa para saber si el servidor ya despertó."""
    return JsonResponse({"ok": True})


class CiudadesView(generics.ListAPIView):
    """GET /api/ciudades/: las ciudades con su número de conciertos próximos."""

    serializer_class = CiudadSerializer
    pagination_class = None  # son pocas: se mandan todas

    def get_queryset(self):
        proximos = Q(recintos__conciertos__fecha_hora__gte=inicio_de_hoy()) & ~Q(
            recintos__conciertos__estado=Concierto.Estado.CANCELADO
        )
        return Ciudad.objects.annotate(conciertos_proximos=Count("recintos__conciertos", filter=proximos))


def leer_fecha(parametros, nombre):
    valor = parametros.get(nombre)
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValidationError({nombre: "Usa el formato AAAA-MM-DD."})


class ConciertosView(generics.ListAPIView):
    """GET /api/conciertos/?ciudad=cdmx&q=texto&desde=AAAA-MM-DD&hasta=AAAA-MM-DD&orden=fecha|precio|nota&pagina=N"""

    serializer_class = ConciertoListaSerializer

    def get_queryset(self):
        parametros = self.request.query_params
        # select_related trae artista, recinto y ciudad en la misma consulta (evita N+1).
        conciertos = anotar_calificacion_artista(
            Concierto.objects.proximos().select_related("artista", "recinto__ciudad")
        )

        if ciudad := parametros.get("ciudad"):
            conciertos = conciertos.filter(recinto__ciudad__slug=ciudad)

        if texto := parametros.get("q", "").strip():
            # unaccent: "electronica" encuentra "Electrónica". Los invitados se buscan con
            # una subconsulta para no repetir el concierto si coinciden varios.
            con_invitado = Concierto.invitados.through.objects.filter(
                artista__nombre__unaccent__icontains=texto
            ).values("concierto_id")
            conciertos = conciertos.filter(
                Q(titulo__unaccent__icontains=texto)
                | Q(artista__nombre__unaccent__icontains=texto)
                | Q(recinto__nombre__unaccent__icontains=texto)
                | Q(genero__unaccent__icontains=texto)
                | Q(artista__genero__unaccent__icontains=texto)  # por si el concierto no tiene género propio
                | Q(pk__in=con_invitado)
            )

        # __date compara el día en la hora de México (TIME_ZONE), no en UTC.
        if desde := leer_fecha(parametros, "desde"):
            conciertos = conciertos.filter(fecha_hora__date__gte=desde)
        if hasta := leer_fecha(parametros, "hasta"):
            conciertos = conciertos.filter(fecha_hora__date__lte=hasta)

        if parametros.get("orden") == "precio":
            # Los que no tienen precio van al final.
            return conciertos.order_by(F("precio_desde").asc(nulls_last=True), "fecha_hora", "pk")
        if parametros.get("orden") == "nota":
            # Mejor reseñados: por la nota de las fechas pasadas del artista; sin reseñas, al final.
            return conciertos.order_by(F("promedio_artista").desc(nulls_last=True), "fecha_hora", "pk")
        return conciertos.order_by("fecha_hora", "pk")


class ConciertoDetalleView(generics.RetrieveAPIView):
    """GET /api/conciertos/<slug>/: incluye pasados y cancelados, por si alguien tiene el enlace."""

    serializer_class = ConciertoDetalleSerializer
    lookup_field = "slug"
    queryset = Concierto.objects.select_related("artista", "recinto__ciudad").prefetch_related("invitados", "precios")


class ArtistaDetalleView(generics.RetrieveAPIView):
    """GET /api/artistas/<slug>/: descripción, redes, fechas próximas y pasadas, estadísticas de reseñas."""

    serializer_class = ArtistaDetalleSerializer
    lookup_field = "slug"
    queryset = Artista.objects.all()


class RecintosView(generics.ListAPIView):
    """GET /api/recintos/?ciudad=cdmx&q=texto: los recintos con conciertos, los más activos primero."""

    serializer_class = RecintoEnListaSerializer

    def get_queryset(self):
        parametros = self.request.query_params
        hoy, cancelado = inicio_de_hoy(), Q(conciertos__estado=Concierto.Estado.CANCELADO)
        proximos = Q(conciertos__fecha_hora__gte=hoy) & ~cancelado
        pasados = Q(conciertos__fecha_hora__lt=hoy) & ~cancelado
        recintos = (
            Recinto.objects.select_related("ciudad")
            .annotate(proximos=Count("conciertos", filter=proximos), pasados=Count("conciertos", filter=pasados))
            .filter(Q(proximos__gt=0) | Q(pasados__gt=0))
        )
        if ciudad := parametros.get("ciudad"):
            recintos = recintos.filter(ciudad__slug=ciudad)
        if texto := parametros.get("q", "").strip():
            recintos = recintos.filter(Q(nombre__unaccent__icontains=texto) | Q(direccion__unaccent__icontains=texto))
        return recintos.order_by("-proximos", "nombre", "pk")


class RecintoDetalleView(generics.RetrieveAPIView):
    """GET /api/recintos/<slug>/: dirección, calificación y sus conciertos próximos y pasados."""

    serializer_class = RecintoDetalleSerializer
    lookup_field = "slug"
    queryset = Recinto.objects.select_related("ciudad")
