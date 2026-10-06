from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from conciertos.models import Artista, Ciudad, Concierto, Recinto

Usuario = get_user_model()
TEXTO = "Tocaron casi dos horas y el sonido estuvo impecable."


class DatosDeResenas(APITestCase):
    """Los Cometas del Sur: una fecha pasada en CDMX, otra en Guadalajara y una futura."""

    def setUp(self):
        cdmx = Ciudad.objects.get(slug="cdmx")
        gdl = Ciudad.objects.get(slug="guadalajara")
        self.auditorio = Recinto.objects.create(nombre="Auditorio Nacional", ciudad=cdmx)
        self.estadio = Recinto.objects.create(nombre="Estadio 3 de Marzo", ciudad=gdl)
        self.cometas = Artista.objects.create(nombre="Los Cometas del Sur")
        ahora = timezone.now()
        self.pasado = self.concierto(self.auditorio, ahora - timedelta(days=10))
        self.pasado_gdl = self.concierto(self.estadio, ahora - timedelta(days=3))
        self.futuro = self.concierto(self.auditorio, ahora + timedelta(days=20))
        self.sofia = Usuario.objects.create_user("sofia@correo.mx", "sofia@correo.mx", "clave-larga-1", first_name="Sofía M.")
        self.diego = Usuario.objects.create_user("diego@correo.mx", "diego@correo.mx", "clave-larga-2", first_name="Diego R.")

    def concierto(self, recinto, fecha, **campos):
        return Concierto.objects.create(
            titulo="Los Cometas del Sur", artista=self.cometas, recinto=recinto,
            fecha_hora=fecha, url_boletos="https://boletos.mx", **campos,
        )

    def como(self, usuario):
        self.client.force_authenticate(usuario)

    def resenar(self, concierto, **campos):
        datos = {"concierto": concierto.slug, "general": 5, "texto": TEXTO, "asistio": True, **campos}
        return self.client.post("/api/resenas/", datos, format="json")
