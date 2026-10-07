from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Value, When
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from conciertos.models import Artista, Concierto, inicio_de_hoy
from conciertos.serializers import (
    ConciertoListaSerializer,
    ConciertoPasadoSerializer,
    conciertos_pasados,
    conciertos_proximos,
)
from resenas.models import Resena

from .models import ArtistaSeguido, ConciertoGuardado

LIMITE_DE_FECHAS = 60


class SeguirArtistaView(APIView):
    """POST sigue, DELETE deja de seguir. /api/artistas/<slug>/seguir/"""

    permission_classes = [permissions.IsAuthenticated]

    def respuesta(self, artista, siguiendo):
        return Response({"siguiendo": siguiendo, "seguidores": artista.seguidores.count()})

    def post(self, request, slug):
        artista = generics.get_object_or_404(Artista, slug=slug)
        ArtistaSeguido.objects.get_or_create(usuario=request.user, artista=artista)
        return self.respuesta(artista, True)

    def delete(self, request, slug):
        artista = generics.get_object_or_404(Artista, slug=slug)
        ArtistaSeguido.objects.filter(usuario=request.user, artista=artista).delete()
        return self.respuesta(artista, False)


class GuardarConciertoView(APIView):
    """POST guarda, DELETE quita. /api/conciertos/<slug>/guardar/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        concierto = generics.get_object_or_404(Concierto, slug=slug)
        ConciertoGuardado.objects.get_or_create(usuario=request.user, concierto=concierto)
        return Response({"guardado": True})

    def delete(self, request, slug):
        concierto = generics.get_object_or_404(Concierto, slug=slug)
        ConciertoGuardado.objects.filter(usuario=request.user, concierto=concierto).delete()
        return Response({"guardado": False})


class MisConciertosView(APIView):
    """GET /api/mis-conciertos/?ciudad=cdmx

    - de_artistas: próximas fechas de los artistas que sigo, las de mi ciudad primero.
    - guardados: los que guardé y aún no pasan; guardados_pasados: los que ya pasaron
      (con "resenaste" para invitar a reseñar los que faltan).
    - artistas: a quién sigo, con cuántas fechas próximas tiene.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        usuario = request.user
        ciudad = request.query_params.get("ciudad", "")
        primero_mi_ciudad = Case(
            When(recinto__ciudad__slug=ciudad, then=Value(0)), default=Value(1), output_field=IntegerField()
        )

        seguidos = Artista.objects.filter(seguidores__usuario=usuario)
        de_artistas = (
            conciertos_proximos(Concierto.objects.filter(artista__in=seguidos))
            .annotate(lejos=primero_mi_ciudad)
            .order_by("lejos", "fecha_hora", "pk")[:LIMITE_DE_FECHAS]
        )

        mios = Concierto.objects.filter(guardados__usuario=usuario)
        guardados = conciertos_proximos(mios)
        resenado = Resena.objects.filter(usuario=usuario, concierto=OuterRef("pk"))
        pasados = conciertos_pasados(mios).annotate(resenaste=Exists(resenado))

        hoy = inicio_de_hoy()
        artistas = seguidos.annotate(
            proximos=Count(
                "conciertos",
                filter=Q(conciertos__fecha_hora__gte=hoy) & ~Q(conciertos__estado=Concierto.Estado.CANCELADO),
            )
        ).order_by("nombre")

        return Response({
            "de_artistas": ConciertoListaSerializer(de_artistas, many=True).data,
            "guardados": ConciertoListaSerializer(guardados, many=True).data,
            "guardados_pasados": [
                {**ConciertoPasadoSerializer(c).data, "resenaste": c.resenaste} for c in pasados
            ],
            "artistas": [
                {"nombre": a.nombre, "slug": a.slug, "imagen_url": a.imagen_url, "proximos": a.proximos} for a in artistas
            ],
        })
