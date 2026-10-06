"""Búsqueda de descripciones en Wikipedia, con respuestas falsas (sin llamar a internet)."""
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from conciertos.importacion.descripciones import actualizar_pendientes
from conciertos.importacion.wikipedia import Wikipedia, articulo_de_url, nombres_coinciden
from conciertos.models import Artista

MB_ROSANA_BRASIL = "48b9a301-c49e-438a-8190-7bee614c4ea9"


def resumen(titulo, texto, descripcion=""):
    return {
        "type": "standard", "title": titulo, "extract": texto, "description": descripcion,
        "content_urls": {"desktop": {"page": f"https://es.wikipedia.org/wiki/{titulo.replace(' ', '_')}"}},
    }


# Lo que "contesta internet" en estas pruebas: el fragmento de la URL basta para distinguir.
RESPUESTAS = {
    "page/summary/Def_Leppard": resumen("Def Leppard", "Def Leppard es una banda británica de hard rock.", "banda británica"),
    "page/summary/Rosana_Arbelo": resumen("Rosana Arbelo", "Rosana Arbelo es una cantautora española.", "cantautora española"),
    "page/summary/Rosana": resumen("Rosana", "Rosana es una cantautora española.", "cantautora española"),
    "page/summary/Travis_Scott": resumen("Travis Scott", "Travis Scott es un rapero estadounidense.", "rapero"),
    "page/summary/Monterrey": resumen("Monterrey", "Monterrey es una ciudad de México.", "ciudad de México"),
    "page/summary/Rosanah_Fienngo": resumen("Rosanah Fienngo", "Rosanah Fienngo es una cantante brasileña.", "cantante"),
    # enwiki "Def Leppard" -> eswiki "Def Leppard"
    "sites=enwiki": {"entities": {"Q1": {"sitelinks": {"eswiki": {"title": "Def Leppard"}}}}},
    # MusicBrainz de la Rosana brasileña -> Wikidata Q16269806 -> solo tiene artículo en inglés y portugués
    f"artist/{MB_ROSANA_BRASIL}": {"relations": [{"url": {"resource": "https://www.wikidata.org/wiki/Q16269806"}}]},
    "ids=Q16269806": {"entities": {"Q16269806": {"sitelinks": {"enwiki": {"title": "Rosanah Fienngo"}}}}},
}
BUSQUEDAS = {
    "Rosana": ["Rosana", "Rosana Arbelo"],
    "Travis": ["Travis Scott", "Travis Barker"],
    "Monterrey": ["Monterrey"],
}


class SesionFalsa:
    def __init__(self):
        self.headers = {}
        self.urls = []

    def get(self, url, params=None, timeout=None):
        params = params or {}
        self.urls.append(url)
        if params.get("list") == "search":
            titulos = BUSQUEDAS.get(params["srsearch"], [])
            return SimpleNamespace(status_code=200, json=lambda: {"query": {"search": [{"title": t} for t in titulos]}})
        clave = url + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        for fragmento, datos in RESPUESTAS.items():
            if fragmento in clave:
                return SimpleNamespace(status_code=200, json=lambda datos=datos: datos)
        return SimpleNamespace(status_code=404, json=lambda: {})


def artista(nombre, **campos):
    return SimpleNamespace(nombre=nombre, wikipedia=campos.get("wikipedia", ""), enlaces=campos.get("enlaces", {}))


class WikipediaTests(SimpleTestCase):
    def setUp(self):
        self.wikipedia = Wikipedia(sesion=SesionFalsa(), pausa_musicbrainz=0)

    def test_enlace_wiki_en_ingles_se_pasa_al_espanol(self):
        def_leppard = artista("Def Leppard", enlaces={"wiki": "https://en.wikipedia.org/wiki/Def_Leppard"})
        encontrado = self.wikipedia.buscar(def_leppard)
        self.assertEqual(encontrado.texto, "Def Leppard es una banda británica de hard rock.")
        self.assertEqual(encontrado.url, "https://es.wikipedia.org/wiki/Def_Leppard")

    def test_musicbrainz_de_otra_persona_no_se_usa(self):
        # Ticketmaster liga a Rosana con la cantante brasileña: se descarta y se busca por nombre.
        rosana = artista("Rosana", enlaces={"musicbrainz": f"https://musicbrainz.org/artist/{MB_ROSANA_BRASIL}"})
        encontrado = self.wikipedia.buscar(rosana)
        self.assertEqual(encontrado.titulo, "Rosana")
        self.assertIn("española", encontrado.texto)

    def test_busqueda_por_nombre_exige_titulo_identico(self):
        self.assertIsNone(self.wikipedia.buscar(artista("Travis")))  # "Travis Scott" no es "Travis"

    def test_busqueda_por_nombre_exige_que_sea_de_musica(self):
        self.assertIsNone(self.wikipedia.buscar(artista("Monterrey")))  # la ciudad, no una banda

    def test_articulo_puesto_a_mano_no_se_verifica(self):
        rosana = artista("Rosana", wikipedia="https://es.wikipedia.org/wiki/Rosana_Arbelo")
        self.assertEqual(self.wikipedia.buscar(rosana).titulo, "Rosana Arbelo")

    def test_utilidades(self):
        self.assertEqual(articulo_de_url("https://es.m.wikipedia.org/wiki/Caf%C3%A9_Tacvba"), ("es", "Café Tacvba"))
        self.assertIsNone(articulo_de_url("https://www.instagram.com/rosanaoficial/"))
        self.assertTrue(nombres_coinciden("Rosana", "Rosana Arbelo"))
        self.assertTrue(nombres_coinciden("Los Ángeles Azules", "Ángeles Azules"))
        self.assertFalse(nombres_coinciden("Rosana", "Rosanah Fienngo"))


class ActualizarDescripcionesTests(TestCase):
    def setUp(self):
        self.wikipedia = Wikipedia(sesion=SesionFalsa(), pausa_musicbrainz=0)

    def test_guarda_la_descripcion_y_su_fuente(self):
        Artista.objects.create(nombre="Rosana")
        self.assertEqual(actualizar_pendientes(wikipedia=self.wikipedia), (1, 0, []))
        rosana = Artista.objects.get()
        self.assertIn("cantautora", rosana.descripcion)
        self.assertEqual(rosana.descripcion_fuente, "https://es.wikipedia.org/wiki/Rosana")
        self.assertIsNotNone(rosana.descripcion_revisada)

    def test_no_toca_las_descripciones_fijas_ni_repite_las_recientes(self):
        Artista.objects.create(nombre="Rosana", descripcion="La escribí yo.", descripcion_fija=True)
        actualizar_pendientes(wikipedia=self.wikipedia)
        self.assertEqual(Artista.objects.get().descripcion, "La escribí yo.")
        # Una ya revisada hoy no se vuelve a pedir.
        Artista.objects.create(nombre="Travis")
        self.assertEqual(actualizar_pendientes(wikipedia=self.wikipedia), (0, 1, []))
        self.assertEqual(actualizar_pendientes(wikipedia=self.wikipedia), (0, 0, []))
