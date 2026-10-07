from rest_framework import generics, permissions
from rest_framework.throttling import ScopedRateThrottle

from .models import Sugerencia
from .serializers import SugerenciaSerializer


class SugerenciasView(generics.ListCreateAPIView):
    """GET: mis sugerencias y en qué van. POST: sugerir un concierto que falta (con sesión)."""

    serializer_class = SugerenciaSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    throttle_scope = "sugerencias"

    def get_throttles(self):
        # El freno solo aplica al enviar, no al consultar.
        return [ScopedRateThrottle()] if self.request.method == "POST" else []

    def get_queryset(self):
        return Sugerencia.objects.filter(usuario=self.request.user).select_related("ciudad", "concierto")

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
