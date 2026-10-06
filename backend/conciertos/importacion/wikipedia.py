"""Busca la descripción de un artista en Wikipedia en español.

Camino, del más confiable al menos:
1. El artículo que pusiste a mano en el panel (campo "artículo de Wikipedia").
2. El enlace "wiki" que manda Ticketmaster (puede ser de otro idioma: se pasa al español con Wikidata).
3. El id de MusicBrainz que manda Ticketmaster -> Wikidata -> Wikipedia en español.
4. Buscar el nombre en Wikipedia: título idéntico al nombre y artículo de música.

Los caminos 2 y 3 a veces apuntan a otra persona con el mismo nombre (pasó con
Rosana: MusicBrainz llevaba a una cantante brasileña). Por eso, salvo en el 1,
el título del artículo debe coincidir con el nombre del artista.

El texto de Wikipedia es CC BY-SA: se muestra siempre con un enlace a su fuente.
"""
import re
import time
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import requests

# Wikipedia y MusicBrainz piden identificarse con un User-Agent que diga quién llama.
AGENTE = "QuienToca/1.0 (https://github.com/runo06/Quien-Toca)"
PAUSA_MUSICBRAINZ = 1.1  # MusicBrainz admite una llamada por segundo
PALABRAS_VACIAS = {"the", "los", "las", "la", "el", "and", "y", "&"}
# Para la búsqueda por nombre: el artículo debe ser de alguien que hace música.
PATRON_MUSICA = re.compile(
    r"cantant|cantaut|banda|grupo|m[uú]sic|rapero|rapera|\bdj\b|compositor|orquesta|d[uú]o\b|"
    r"productor|mariachi|conjunto|tr[ií]o\b|pianista|guitarrista|vocalista|int[eé]rprete|sonidero|disc jockey",
    re.IGNORECASE,
)


class ErrorWikipedia(Exception):
    """No se pudo consultar (red, servidor caído): se reintenta otra noche."""


@dataclass(frozen=True)
class Resumen:
    titulo: str
    texto: str
    url: str
    descripcion_corta: str = ""  # la de Wikidata: "cantautora española", "banda de rock"

    def es_de_musica(self):
        return bool(PATRON_MUSICA.search(f"{self.descripcion_corta} {self.texto[:250]}"))


def palabras(texto):
    """Palabras en minúsculas y sin acentos, sin lo que va entre paréntesis ("Rosana (cantante)")."""
    texto = re.sub(r"\(.*?\)", " ", texto)
    sin_acentos = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z0-9]+", sin_acentos)) - PALABRAS_VACIAS


def nombres_coinciden(nombre_artista, titulo):
    """"Rosana" y "Rosana Arbelo" sí; "Rosana" y "Rosanah Fienngo" no."""
    artista, articulo = palabras(nombre_artista), palabras(titulo)
    return bool(artista) and bool(articulo) and (artista <= articulo or articulo <= artista)


def articulo_de_url(url):
    """https://en.wikipedia.org/wiki/Def_Leppard -> ("en", "Def Leppard"); None si no es de Wikipedia."""
    partes = urlparse(url)
    coincidencia = re.match(r"^([a-z\-]+)\.(?:m\.)?wikipedia\.org$", partes.netloc)
    if not coincidencia or not partes.path.startswith("/wiki/"):
        return None
    return coincidencia.group(1), unquote(partes.path[len("/wiki/"):]).replace("_", " ")


def id_de_musicbrainz(url):
    coincidencia = re.search(r"/artist/([0-9a-f\-]{36})", url or "")
    return coincidencia.group(1) if coincidencia else None


class Wikipedia:
    def __init__(self, sesion=None, pausa_musicbrainz=PAUSA_MUSICBRAINZ):
        self.sesion = sesion or requests.Session()
        self.sesion.headers.update({"User-Agent": AGENTE, "Accept": "application/json"})
        self.pausa_musicbrainz = pausa_musicbrainz

    def _json(self, url, **parametros):
        try:
            respuesta = self.sesion.get(url, params=parametros or None, timeout=20)
        except requests.RequestException as error:
            raise ErrorWikipedia(str(error)) from error
        if respuesta.status_code == 404:
            return None
        if respuesta.status_code >= 400:
            raise ErrorWikipedia(f"{url} respondió {respuesta.status_code}")
        return respuesta.json()

    def titulo_en_espanol(self, idioma, titulo):
        """El artículo equivalente en Wikipedia en español (Wikidata sabe cuál es)."""
        if idioma == "es":
            return titulo
        datos = self._json(
            "https://www.wikidata.org/w/api.php",
            action="wbgetentities", sites=f"{idioma}wiki", titles=titulo, props="sitelinks", format="json",
        )
        for entidad in (datos or {}).get("entities", {}).values():
            if eswiki := entidad.get("sitelinks", {}).get("eswiki"):
                return eswiki["title"]
        return None

    def titulo_desde_musicbrainz(self, mbid):
        time.sleep(self.pausa_musicbrainz)
        datos = self._json(f"https://musicbrainz.org/ws/2/artist/{mbid}", inc="url-rels", fmt="json")
        for relacion in (datos or {}).get("relations", []):
            recurso = relacion.get("url", {}).get("resource", "")
            if coincidencia := re.search(r"wikidata\.org/wiki/(Q\d+)", recurso):
                entidad = self._json(
                    "https://www.wikidata.org/w/api.php",
                    action="wbgetentities", ids=coincidencia.group(1), props="sitelinks", format="json",
                )
                eswiki = (entidad or {}).get("entities", {}).get(coincidencia.group(1), {}).get("sitelinks", {}).get("eswiki")
                return eswiki["title"] if eswiki else None
        return None

    def resumen(self, titulo):
        """El primer párrafo del artículo. None si no existe o es una página de desambiguación."""
        datos = self._json(f"https://es.wikipedia.org/api/rest_v1/page/summary/{titulo.replace(' ', '_')}")
        if not datos or datos.get("type") != "standard" or not datos.get("extract"):
            return None
        return Resumen(
            titulo=datos["title"],
            texto=datos["extract"].strip(),
            url=datos.get("content_urls", {}).get("desktop", {}).get("page", ""),
            descripcion_corta=datos.get("description", ""),
        )

    def buscar_por_nombre(self, nombre):
        """Último recurso: buscar el nombre en Wikipedia. Solo vale un artículo de música
        cuyo título sea exactamente el nombre ("Kurt (cantante)" sí; "Travis Scott" para "Travis" no)."""
        datos = self._json(
            "https://es.wikipedia.org/w/api.php",
            action="query", list="search", srsearch=nombre, srlimit=5, srnamespace=0, format="json",
        )
        for resultado in (datos or {}).get("query", {}).get("search", []):
            if palabras(resultado["title"]) != palabras(nombre):
                continue
            resumen = self.resumen(resultado["title"])
            if resumen and resumen.es_de_musica():
                return resumen
        return None

    def buscar(self, artista):
        """El resumen para este artista, o None si no hay uno confiable."""
        if artista.wikipedia:
            articulo = articulo_de_url(artista.wikipedia)
            titulo = self.titulo_en_espanol(*articulo) if articulo else None
            return self.resumen(titulo) if titulo else None  # lo eligió una persona: no se verifica

        titulo = None
        if (articulo := articulo_de_url(artista.enlaces.get("wiki", ""))):
            titulo = self.titulo_en_espanol(*articulo)
        if not titulo and (mbid := id_de_musicbrainz(artista.enlaces.get("musicbrainz"))):
            titulo = self.titulo_desde_musicbrainz(mbid)
        resumen = self.resumen(titulo) if titulo else None
        if resumen and nombres_coinciden(artista.nombre, resumen.titulo):
            return resumen
        return self.buscar_por_nombre(artista.nombre)
