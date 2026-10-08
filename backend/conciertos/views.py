from datetime import date

from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.http import JsonResponse
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from resenas.calificaciones import anotar_calificacion_artista

from .importacion import artistas_externos
from .models import Artista, Ciudad, Concierto, Recinto, inicio_de_hoy
from .serializers import (
    ArtistaDetalleSerializer,
    ArtistaEnListaSerializer,
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


class ArtistasView(generics.ListAPIView):
    """GET /api/artistas/?q=texto: perfiles de artista para el buscador (también los que no tienen fechas).

    Primero el nombre exacto, luego los que empiezan igual y después los que tienen más fechas.
    """

    serializer_class = ArtistaEnListaSerializer
    pagination_class = None
    LIMITE = 6

    def get_queryset(self):
        texto = self.request.query_params.get("q", "").strip()
        if len(texto) < 2:
            return Artista.objects.none()
        hoy = inicio_de_hoy()
        parecido = Case(
            When(nombre__unaccent__iexact=texto, then=Value(0)),
            When(nombre__unaccent__istartswith=texto, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
        return (
            Artista.objects.filter(nombre__unaccent__icontains=texto)
            .annotate(
                parecido=parecido,
                proximos=Count(
                    "conciertos",
                    filter=Q(conciertos__fecha_hora__gte=hoy) & ~Q(conciertos__estado=Concierto.Estado.CANCELADO),
                ),
            )
            .order_by("parecido", "-proximos", "nombre")[: self.LIMITE]
        )


class ArtistasExternosView(APIView):
    """GET /api/artistas/externos/?q=texto: artistas de Ticketmaster que aún no tenemos.
    POST /api/artistas/externos/<id>/: crea su perfil (cuando alguien lo abre) y devuelve su slug."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "externos"

    def get(self, request, id_ticketmaster=None):
        texto = request.query_params.get("q", "").strip()
        if len(texto) < 3:
            return Response([])
        try:
            return Response(artistas_externos.buscar(texto))
        except artistas_externos.SinTicketmaster:
            return Response([])  # sin Ticketmaster solo se ven los artistas que ya tenemos

    def post(self, request, id_ticketmaster):
        try:
            artista = artistas_externos.crear(id_ticketmaster)
        except artistas_externos.SinTicketmaster:
            return Response({"detail": "Ticketmaster no respondió. Inténtalo en un momento."}, status=503)
        if artista is None:
            return Response({"detail": "No encontramos a ese artista."}, status=404)
        return Response({"slug": artista.slug, "nombre": artista.nombre})
