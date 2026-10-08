"""Artistas que aún no están en la base, buscados en Ticketmaster al momento.

Al buscar solo se muestran; el perfil se crea cuando alguien lo abre. Así una búsqueda
cualquiera no llena la base de artistas que nadie quería.
"""
import hashlib
import re

from django.conf import settings
from django.core.cache import cache

from conciertos.models import Artista

from .cliente import ClienteTicketmaster, ErrorTicketmaster
from .descripciones import actualizar_descripcion
from .importador import Importador
from .traducir import elegir_imagen, traducir_artista, traducir_genero
from .wikipedia import ErrorWikipedia, Wikipedia, palabras

UN_DIA = 60 * 60 * 24
MAXIMO = 4
# Ticketmaster también devuelve tributos y fiestas temáticas ("Bad Bunny Rave"): no son el artista.
PATRON_NO_ARTISTA = re.compile(
    r"\b(tribut\w*|homenaje|rave|night|nights|noche|party|fiesta|experience|experiencia|"
    r"sinf[oó]nico|symphonic|karaoke|cover|covers|vs\.?)\b",
    re.IGNORECASE,
)


class SinTicketmaster(Exception):
    """No hay clave o Ticketmaster no respondió."""


def cliente():
    try:
        return ClienteTicketmaster(settings.TICKETMASTER_API_KEY, pausa=0)
    except ErrorTicketmaster as error:
        raise SinTicketmaster(str(error)) from error


def resumen(atraccion):
    return {
        "id_ticketmaster": atraccion["id"],
        "nombre": atraccion["name"].strip(),
        "imagen_url": elegir_imagen(atraccion.get("images")),
        "genero": traducir_genero(atraccion.get("classifications")),
        "fechas": (atraccion.get("upcomingEvents") or {}).get("_total", 0),
    }


def parece_el_artista(atraccion, texto):
    """Cada palabra buscada es el inicio de alguna del nombre (se busca mientras se escribe:
    "vicente fer" encuentra "Vicente Fernández"), y no suena a tributo o fiesta."""
    nombre = atraccion.get("name") or ""
    del_nombre = palabras(nombre)
    buscadas = palabras(texto)
    return (
        bool(buscadas)
        and all(any(n.startswith(b) for n in del_nombre) for b in buscadas)
        and not PATRON_NO_ARTISTA.search(nombre)
    )


def buscar(texto):
    """Hasta 4 artistas de Ticketmaster que no tenemos. Las búsquedas se recuerdan un día."""
    texto = " ".join(texto.split())[:80]
    clave = "artistas-tm:" + hashlib.sha1(texto.lower().encode()).hexdigest()
    encontrados = cache.get(clave)
    if encontrados is None:
        try:
            atracciones = cliente().buscar_artistas(texto)
            if not atracciones and " " in texto:
                # Ticketmaster no entiende palabras a medias ("vicente fer"): se busca sin la
                # última y el filtro de abajo se queda con las que empiezan como lo escrito.
                atracciones = cliente().buscar_artistas(texto.rsplit(" ", 1)[0])
        except (ErrorTicketmaster, OSError) as error:
            raise SinTicketmaster(str(error)) from error
        candidatos = [a for a in atracciones if a.get("id") and a.get("name") and parece_el_artista(a, texto)]
        # Los artistas de verdad suelen traer redes: van primero; luego el nombre exacto y los que tienen fechas.
        candidatos.sort(key=lambda a: (
            not a.get("externalLinks"),
            palabras(a["name"]) != palabras(texto),
            -(a.get("upcomingEvents") or {}).get("_total", 0),
        ))
        encontrados = [resumen(a) for a in candidatos]
        cache.set(clave, encontrados, UN_DIA)
    ya_tenemos = set(
        Artista.objects.filter(id_ticketmaster__in=[e["id_ticketmaster"] for e in encontrados])
        .values_list("id_ticketmaster", flat=True)
    )
    return [e for e in encontrados if e["id_ticketmaster"] not in ya_tenemos][:MAXIMO]


def crear(id_ticketmaster):
    """El perfil del artista (lo crea si no existe) con su imagen, género, redes y descripción.

    Devuelve None si Ticketmaster no lo conoce o no es de música.
    """
    if existente := Artista.objects.filter(id_ticketmaster=id_ticketmaster).first():
        return existente
    try:
        atraccion = cliente().artista(id_ticketmaster)
    except (ErrorTicketmaster, OSError) as error:
        raise SinTicketmaster(str(error)) from error
    segmentos = {(c.get("segment") or {}).get("name") for c in (atraccion or {}).get("classifications") or []}
    if not atraccion or "Music" not in segmentos:
        return None
    artista = Importador()._artista(traducir_artista(atraccion))
    try:
        actualizar_descripcion(artista, Wikipedia())
    except ErrorWikipedia:
        pass  # la búsqueda de la noche lo vuelve a intentar
    return artista
