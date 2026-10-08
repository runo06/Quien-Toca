"""Artistas buscados en Ticketmaster al momento, con el cliente simulado (sin llamar a la API)."""
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from conciertos.importacion.wikipedia import ErrorWikipedia
from conciertos.models import Artista


def atraccion(id_, nombre, enlaces=None, fechas=0, segmento="Music"):
    return {
        "id": id_, "name": nombre, "upcomingEvents": {"_total": fechas},
        "externalLinks": enlaces or {},
        "images": [{"url": f"https://img/{id_}.jpg", "ratio": "16_9", "width": 1024, "fallback": False}],
        "classifications": [{"segment": {"name": segmento}, "genre": {"name": "Latin"}}],
    }


CHENTE = atraccion("TM-CHENTE", "Vicente Fernandez", {"musicbrainz": [{"url": "https://musicbrainz.org/artist/x"}]})
BUSQUEDA = [
    atraccion("TM-RAVE", "Vicente Fernandez Rave Night"),  # fiesta: fuera
    atraccion("TM-JR", "Vicente Fernandez, Jr.", fechas=2),
    CHENTE,
    atraccion("TM-OTRO", "Alejandro Fernandez"),  # no tiene "vicente": fuera
]


class ClienteFalso:
    llamadas = []

    def __init__(self, *args, **kwargs):
        pass

    def buscar_artistas(self, texto, cuantos=10):
        ClienteFalso.llamadas.append(texto)
        # Como Ticketmaster: entiende palabras completas, no "fer".
        return BUSQUEDA if texto.lower() in ("vicente fernandez", "vicente") else []

    def artista(self, id_):
        return {"TM-CHENTE": CHENTE, "TM-TEATRO": atraccion("TM-TEATRO", "Cats", segmento="Arts & Theatre")}.get(id_)


@override_settings(TICKETMASTER_API_KEY="clave-de-prueba")
@patch("conciertos.importacion.artistas_externos.ClienteTicketmaster", ClienteFalso)
@patch("conciertos.importacion.artistas_externos.Wikipedia.buscar", side_effect=ErrorWikipedia("sin red en pruebas"))
class ArtistasExternosTests(APITestCase):
    def setUp(self):
        cache.clear()
        ClienteFalso.llamadas = []

    def buscar(self, q):
        return self.client.get("/api/artistas/externos/", {"q": q}).data

    def test_filtra_tributos_y_otros_nombres_y_prioriza_los_que_tienen_redes(self, _wikipedia):
        self.assertEqual([a["nombre"] for a in self.buscar("vicente fernandez")], ["Vicente Fernandez", "Vicente Fernandez, Jr."])

    def test_palabra_a_medias_se_busca_sin_ella_y_se_filtra_por_inicio(self, _wikipedia):
        resultado = self.buscar("vicente fer")
        self.assertEqual(ClienteFalso.llamadas, ["vicente fer", "vicente"])
        self.assertEqual([a["nombre"] for a in resultado], ["Vicente Fernandez", "Vicente Fernandez, Jr."])

    def test_las_busquedas_se_recuerdan_un_dia(self, _wikipedia):
        self.buscar("vicente fernandez")
        self.buscar("Vicente  Fernandez")
        self.assertEqual(ClienteFalso.llamadas, ["vicente fernandez"])

    def test_no_muestra_los_que_ya_tenemos(self, _wikipedia):
        Artista.objects.create(nombre="Vicente Fernandez", id_ticketmaster="TM-CHENTE")
        self.assertEqual([a["nombre"] for a in self.buscar("vicente fernandez")], ["Vicente Fernandez, Jr."])

    def test_texto_corto_no_consulta(self, _wikipedia):
        self.assertEqual(self.buscar("vi"), [])
        self.assertEqual(ClienteFalso.llamadas, [])

    def test_abrir_crea_el_perfil_una_sola_vez(self, _wikipedia):
        respuesta = self.client.post("/api/artistas/externos/TM-CHENTE/")
        self.assertEqual(respuesta.data, {"slug": "vicente-fernandez", "nombre": "Vicente Fernandez"})
        chente = Artista.objects.get(id_ticketmaster="TM-CHENTE")
        self.assertEqual((chente.genero, chente.imagen_url), ("Latino", "https://img/TM-CHENTE.jpg"))
        self.assertIn("musicbrainz", chente.enlaces)  # para buscar su descripción
        self.client.post("/api/artistas/externos/TM-CHENTE/")
        self.assertEqual(Artista.objects.filter(id_ticketmaster="TM-CHENTE").count(), 1)

    def test_solo_artistas_de_musica_que_existen(self, _wikipedia):
        self.assertEqual(self.client.post("/api/artistas/externos/TM-TEATRO/").status_code, 404)
        self.assertEqual(self.client.post("/api/artistas/externos/NO-EXISTE/").status_code, 404)
        self.assertFalse(Artista.objects.exists())

    @override_settings(TICKETMASTER_API_KEY="")
    def test_sin_clave_no_falla(self, _wikipedia):
        from conciertos.importacion.cliente import ClienteTicketmaster

        with patch("conciertos.importacion.artistas_externos.ClienteTicketmaster", ClienteTicketmaster):  # el real
            self.assertEqual(self.buscar("vicente fernandez"), [])
            self.assertEqual(self.client.post("/api/artistas/externos/TM-CHENTE/").status_code, 503)
