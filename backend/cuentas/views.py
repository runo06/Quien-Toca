from django.contrib.auth import authenticate
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import EntrarSerializer, RegistroSerializer, UsuarioSerializer


def respuesta_con_tokens(usuario, codigo=status.HTTP_200_OK):
    """El usuario y sus dos tokens: access (corto, para cada petición) y refresh (para pedir otro access)."""
    refresh = RefreshToken.for_user(usuario)
    return Response(
        {"usuario": UsuarioSerializer(usuario).data, "access": str(refresh.access_token), "refresh": str(refresh)},
        status=codigo,
    )


class RegistroView(APIView):
    """POST /api/cuentas/registro/ {nombre, email, password}: crea la cuenta y deja la sesión iniciada."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cuentas"

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return respuesta_con_tokens(serializer.save(), status.HTTP_201_CREATED)


class EntrarView(APIView):
    """POST /api/cuentas/entrar/ {email, password}"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cuentas"

    def post(self, request):
        serializer = EntrarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = authenticate(
            request, username=serializer.validated_data["email"].lower(), password=serializer.validated_data["password"]
        )
        if usuario is None:
            # El mismo mensaje si falla el correo o la contraseña: no se revela qué correos existen.
            return Response({"detail": "Correo o contraseña incorrectos."}, status=status.HTTP_401_UNAUTHORIZED)
        return respuesta_con_tokens(usuario)


class SalirView(APIView):
    """POST /api/cuentas/salir/ {refresh}: anula el token de renovación (el access caduca solo en minutos)."""

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh", "")).blacklist()
        except TokenError:
            pass  # ya caducado o inválido: igual la sesión queda cerrada
        return Response(status=status.HTTP_205_RESET_CONTENT)


class YoView(APIView):
    """GET /api/cuentas/yo/: quién tiene la sesión iniciada."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)
