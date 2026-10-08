"""API de la sección "Editar" de la página. Todo exige el rol Editor."""
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from conciertos.captura_gira import crear_gira
from conciertos.importacion.descripciones import actualizar_descripcion
from conciertos.importacion.wikipedia import ErrorWikipedia, Wikipedia
from conciertos.models import Artista, Concierto, Recinto
from conciertos.serializers import ConciertoListaSerializer
from resenas import moderacion
from resenas.models import Reporte
from sugerencias.aprobar import aprobar, rechazar
from sugerencias.models import Sugerencia

from .roles import EsEditor
from .serializers import (
    ArtistaEdicionSerializer,
    ArtistaOpcionSerializer,
    ConciertoEdicionSerializer,
    GiraSerializer,
    RecintoOpcionSerializer,
    ReporteRevisionSerializer,
    SugerenciaRevisionSerializer,
)

MAXIMO_OPCIONES = 10


class VistaDeEditor(APIView):
    permission_classes = [EsEditor]


class ResumenView(VistaDeEditor):
    """GET /api/edicion/: cuántas sugerencias y reportes esperan revisión."""

    def get(self, request):
        return Response({
            "sugerencias_pendientes": Sugerencia.objects.filter(estado=Sugerencia.Estado.PENDIENTE).count(),
            "reportes_pendientes": Reporte.objects.filter(estado=Reporte.Estado.PENDIENTE).count(),
        })


def buscar_descripcion_si_hace_falta(artista):
    """Si pegaste un artículo de Wikipedia (y la descripción no es tuya), se busca en ese momento.
    Sin artículo, la búsqueda de cada noche lo intenta por nombre."""
    if artista.descripcion_fija or not artista.wikipedia:
        return
    try:
        actualizar_descripcion(artista, Wikipedia())
    except ErrorWikipedia:
        pass  # sin conexión con Wikipedia: la búsqueda de la noche lo vuelve a intentar


class ArtistasView(generics.ListCreateAPIView):
    """GET ?q= para buscar (autocompletado); POST para dar de alta uno nuevo (basta el nombre)."""

    permission_classes = [EsEditor]
    pagination_class = None

    def get_serializer_class(self):
        return ArtistaEdicionSerializer if self.request.method == "POST" else ArtistaOpcionSerializer

    def perform_create(self, serializer):
        buscar_descripcion_si_hace_falta(serializer.save())

    def get_queryset(self):
        texto = self.request.query_params.get("q", "").strip()
        if not texto:
            return Artista.objects.none()
        return Artista.objects.filter(nombre__unaccent__icontains=texto).order_by("nombre")[:MAXIMO_OPCIONES]

    def create(self, request, *args, **kwargs):
        # Si ya existe con ese nombre (sin importar acentos ni mayúsculas), se devuelve ese.
        nombre = str(request.data.get("nombre", "")).strip()
        if existente := Artista.objects.filter(nombre__unaccent__iexact=nombre).first():
            return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)


class ArtistaView(generics.RetrieveUpdateAPIView):
    """GET y PATCH /api/edicion/artistas/<slug>/: nombre, imagen, descripción, Wikipedia y redes."""

    serializer_class = ArtistaEdicionSerializer
    permission_classes = [EsEditor]
    lookup_field = "slug"
    http_method_names = ["get", "patch", "options"]
    queryset = Artista.objects.all()

    def perform_update(self, serializer):
        cambio_wikipedia = "wikipedia" in serializer.validated_data
        artista = serializer.save()
        if cambio_wikipedia:
            buscar_descripcion_si_hace_falta(artista)


class RecintosView(generics.ListCreateAPIView):
    """GET ?q=&ciudad= para buscar; POST {nombre, ciudad, direccion} para dar de alta uno nuevo."""

    serializer_class = RecintoOpcionSerializer
    permission_classes = [EsEditor]
    pagination_class = None

    def get_queryset(self):
        parametros = self.request.query_params
        texto = parametros.get("q", "").strip()
        if not texto:
            return Recinto.objects.none()
        recintos = Recinto.objects.select_related("ciudad").filter(nombre__unaccent__icontains=texto)
        if ciudad := parametros.get("ciudad"):
            recintos = recintos.filter(ciudad__slug=ciudad)
        return recintos.order_by("nombre")[:MAXIMO_OPCIONES]

    def create(self, request, *args, **kwargs):
        nombre = str(request.data.get("nombre", "")).strip()
        ciudad = request.data.get("ciudad")
        existente = Recinto.objects.filter(nombre__unaccent__iexact=nombre, ciudad__slug=ciudad).first()
        if existente:
            return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)


class GiraView(VistaDeEditor):
    """POST /api/edicion/giras/: los datos comunes y una lista de fechas; crea todas o ninguna."""

    def post(self, request):
        serializer = GiraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        creados = crear_gira(datos, datos["fechas"])
        return Response(ConciertoListaSerializer(creados, many=True).data, status=status.HTTP_201_CREATED)


class ConciertoView(generics.RetrieveUpdateAPIView):
    """GET y PATCH /api/edicion/conciertos/<slug>/ (cambiar datos, cancelar, posponer...)."""

    serializer_class = ConciertoEdicionSerializer
    permission_classes = [EsEditor]
    lookup_field = "slug"
    http_method_names = ["get", "patch", "options"]
    queryset = Concierto.objects.select_related("artista", "recinto__ciudad")


class SugerenciasView(generics.ListAPIView):
    """GET /api/edicion/sugerencias/?estado=pendiente (por defecto)."""

    serializer_class = SugerenciaRevisionSerializer
    permission_classes = [EsEditor]
    pagination_class = None

    def get_queryset(self):
        estado = self.request.query_params.get("estado", Sugerencia.Estado.PENDIENTE)
        return Sugerencia.objects.filter(estado=estado).select_related("ciudad", "usuario", "concierto").order_by("fecha")


class RevisarSugerenciaView(VistaDeEditor):
    """POST .../<id>/aprobar/ {artista, recinto} (correcciones opcionales) o .../<id>/rechazar/ {motivo}."""

    def post(self, request, pk, accion):
        sugerencia = generics.get_object_or_404(Sugerencia, pk=pk)
        if sugerencia.estado != Sugerencia.Estado.PENDIENTE:
            return Response({"detail": "Esta sugerencia ya se revisó."}, status=status.HTTP_400_BAD_REQUEST)
        if accion == "aprobar":
            # Se puede corregir el nombre antes de aprobar ("cafe tacuba" -> "Café Tacvba").
            for campo in ("artista", "recinto"):
                if valor := str(request.data.get(campo, "")).strip():
                    setattr(sugerencia, campo, valor)
            sugerencia.save(update_fields=["artista", "recinto"])
            concierto = aprobar(sugerencia)
            return Response({"estado": sugerencia.estado, "concierto": concierto.slug})
        rechazar(sugerencia, str(request.data.get("motivo", "")).strip()[:300])
        return Response({"estado": sugerencia.estado})


class ReportesView(generics.ListAPIView):
    """GET /api/edicion/reportes/: los pendientes, con la reseña y cuántos reportes suma."""

    serializer_class = ReporteRevisionSerializer
    permission_classes = [EsEditor]
    pagination_class = None

    def get_queryset(self):
        return (
            Reporte.objects.filter(estado=Reporte.Estado.PENDIENTE)
            .select_related("usuario", "resena__usuario", "resena__concierto__artista", "resena__concierto__recinto__ciudad")
            .annotate(reportes_de_la_resena=Count("resena__reportes", filter=Q(resena__reportes__estado=Reporte.Estado.PENDIENTE)))
            .order_by("-reportes_de_la_resena", "creado")
        )


class RevisarReporteView(VistaDeEditor):
    """POST .../<id>/aceptar/ (oculta la reseña) o .../<id>/descartar/."""

    def post(self, request, pk, accion):
        reportes = Reporte.objects.filter(pk=pk, estado=Reporte.Estado.PENDIENTE)
        if not reportes.exists():
            return Response({"detail": "Este reporte ya se revisó."}, status=status.HTTP_400_BAD_REQUEST)
        if accion == "aceptar":
            ocultas, resueltos = moderacion.aceptar(reportes)
            return Response({"resenas_ocultas": ocultas, "reportes_resueltos": resueltos})
        return Response({"reportes_resueltos": moderacion.descartar(reportes)})
