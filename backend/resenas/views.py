from django.db.models import Count, Exists, OuterRef, Value
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Reporte, Resena, VotoUtil
from .serializers import ReporteSerializer, ResenaSerializer


class EsAutorOSoloLectura(permissions.BasePermission):
    """Cualquiera lee; solo quien la escribió edita o borra su reseña."""

    message = "Solo puedes cambiar tus propias reseñas."

    def has_object_permission(self, request, view, resena):
        return request.method in permissions.SAFE_METHODS or resena.usuario_id == request.user.pk


def resenas_para(request):
    """Las reseñas visibles con sus votos y, si hay sesión, si a esta persona le sirvió cada una."""
    resenas = (
        Resena.objects.visibles()
        .select_related("usuario", "concierto__artista", "concierto__recinto__ciudad")
        .annotate(utiles=Count("votos"))
    )
    if request.user.is_authenticated:
        voto = VotoUtil.objects.filter(resena=OuterRef("pk"), usuario=request.user)
        return resenas.annotate(me_sirvio=Exists(voto))
    return resenas.annotate(me_sirvio=Value(False))


class ResenasView(generics.ListCreateAPIView):
    """GET /api/resenas/?concierto=&artista=&recinto=&ciudad=  ·  POST /api/resenas/ (con sesión)

    Primero las que más le sirvieron a la gente, luego las más nuevas.
    """

    serializer_class = ResenaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        resenas = resenas_para(self.request)
        filtros = {
            "concierto": "concierto__slug",
            "artista": "concierto__artista__slug",
            "recinto": "concierto__recinto__slug",
            "ciudad": "concierto__recinto__ciudad__slug",
        }
        for parametro, campo in filtros.items():
            if valor := self.request.query_params.get(parametro):
                resenas = resenas.filter(**{campo: valor})
        return resenas.order_by("-utiles", "-creada", "-pk")


class ResenaDetalleView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PATCH y DELETE /api/resenas/<id>/"""

    serializer_class = ResenaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, EsAutorOSoloLectura]
    http_method_names = ["get", "patch", "delete", "options"]

    def get_queryset(self):
        return resenas_para(self.request)


class MisResenasView(APIView):
    """GET /api/resenas/mias/: qué conciertos ya reseñé (para no ofrecerlos en el formulario)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        mias = Resena.objects.filter(usuario=request.user).values("id", "concierto__slug")
        return Response([{"id": r["id"], "concierto": r["concierto__slug"]} for r in mias])


def resena_ajena(request, pk):
    """La reseña visible con ese id; error si es de quien hace la petición."""
    resena = generics.get_object_or_404(Resena.objects.visibles(), pk=pk)
    if resena.usuario_id == request.user.pk:
        raise PermissionDenied("Esta reseña es tuya.")
    return resena


class MeSirvioView(APIView):
    """POST marca "Me sirvió"; DELETE lo quita. /api/resenas/<id>/util/"""

    permission_classes = [permissions.IsAuthenticated]

    def respuesta(self, resena, me_sirvio):
        return Response({"utiles": resena.votos.count(), "me_sirvio": me_sirvio})

    def post(self, request, pk):
        resena = resena_ajena(request, pk)
        VotoUtil.objects.get_or_create(usuario=request.user, resena=resena)
        return self.respuesta(resena, True)

    def delete(self, request, pk):
        resena = resena_ajena(request, pk)
        VotoUtil.objects.filter(usuario=request.user, resena=resena).delete()
        return self.respuesta(resena, False)


class ReportarView(APIView):
    """POST /api/resenas/<id>/reportar/ {motivo, comentario}: queda pendiente para el panel."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        resena = resena_ajena(request, pk)
        if Reporte.objects.filter(usuario=request.user, resena=resena).exists():
            raise ValidationError({"detail": "Ya reportaste esta reseña. La revisaremos pronto."})
        serializer = ReporteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(usuario=request.user, resena=resena)
        return Response(status=status.HTTP_201_CREATED)
