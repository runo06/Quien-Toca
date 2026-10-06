"""Traduce un evento de Ticketmaster a los datos de ¿Quién toca?

No toca la base de datos ni la red: recibe el diccionario del evento y las
ciudades, y devuelve un DatosConcierto o lanza Descartado con el motivo.
"""
import math
import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from conciertos.models import Concierto

ZONA_PREDETERMINADA = "America/Mexico_City"
ANCHO_IDEAL_IMAGEN = 1024  # suficiente para el cartel grande sin cargar imágenes enormes

# Eventos que no son el concierto en sí, sino un producto aparte (fase 0).
PATRON_COMPLEMENTO = re.compile(
    r"estacionamiento|parking|paquete|\bvip\b|hospitality|experiencia|upgrade|souvenir|merch"
    r"|meet\s*(&|and|y)\s*greet|\bm&g\b|polaroid|pre-?signed|hi[\s-]?touch|hi[\s-]?bye"
    r"|boleto de evento no incluido|no da acceso|sin boleto",
    re.IGNORECASE,
)
# Eventos de prueba que Ticketmaster deja publicados ("Evento Demo Platinum HSBC", "EVENTO PRUEBA").
PATRON_PRUEBA = re.compile(r"\bevento\s+(demo|prueba)\b", re.IGNORECASE)
# Los abonos y boletos "Individual" sí son el boleto de un festival, pero vienen
# repetidos por tipo (General, Comfort Pass, Banamex Plus): se agrupan en un solo concierto.
PATRON_ABONO = re.compile(r"^\s*(abono|individual)\b", re.IGNORECASE)

ESTADOS = {
    "onsale": Concierto.Estado.EN_VENTA,
    "offsale": Concierto.Estado.SIN_VENTA,
    "cancelled": Concierto.Estado.CANCELADO,
    "canceled": Concierto.Estado.CANCELADO,
    "postponed": Concierto.Estado.POSPUESTO,
    "rescheduled": Concierto.Estado.REPROGRAMADO,
}

# Ticketmaster entrega los géneros en inglés. Los que no estén aquí se dejan como vienen.
GENEROS = {
    "Latin": "Latino",
    "Rock": "Rock",
    "Pop": "Pop",
    "Ballads/Romantic": "Baladas",
    "Hip-Hop/Rap": "Hip hop",
    "Dance/Electronic": "Electrónica",
    "World": "Música del mundo",
    "Jazz": "Jazz",
    "Alternative": "Alternativo",
    "Metal": "Metal",
    "R&B": "R&B",
    "Country": "Country",
    "Classical": "Clásica",
    "Blues": "Blues",
    "Reggae": "Reggae",
    "Folk": "Folk",
    "Children's Music": "Infantil",
    "Religious": "Religiosa",
}
GENEROS_SIN_DATO = {"Undefined", "Other"}

# Algunos recintos se dan de alta como "artista" para todo su programa: en Bellas Artes,
# la ópera, la danza y las orquestas llegan con la atracción "Sala Principal Bellas Artes".
# Para comparar nombres se ignoran estas palabras genéricas.
PALABRAS_DE_LUGAR = {
    "sala", "principal", "teatro", "auditorio", "foro", "palacio", "recinto", "escenario",
    "arena", "estadio", "explanada", "salon", "centro", "plaza",
}
CONECTORES = {"de", "del", "la", "el", "los", "las", "y"}
# Lo que sobra al final de esos títulos: ", 10+. Ingreso 19:30 h."
PATRON_COLA_DEL_TITULO = re.compile(r"(,?\s*\d{1,2}\s*\+|\.?\s*ingreso\s+\d).*$", re.IGNORECASE)


class Descartado(Exception):
    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


@dataclass(frozen=True)
class DatosArtista:
    id_ticketmaster: str | None  # None si salió del título del evento
    nombre: str
    genero: str
    imagen_url: str


@dataclass(frozen=True)
class DatosRecinto:
    id_ticketmaster: str
    nombre: str
    direccion: str
    latitud: float
    longitud: float
    ciudad: object  # instancia de Ciudad


@dataclass
class DatosConcierto:
    id_ticketmaster: str
    titulo: str
    fecha_hora: datetime
    hora_por_confirmar: bool
    estado: str
    url_boletos: str
    imagen_url: str
    genero: str
    precio_desde: Decimal | None
    moneda: str
    recinto: DatosRecinto
    artista: DatosArtista
    invitados: list = field(default_factory=list)
    # Ids de "atracciones" que en realidad eran el recinto: el importador limpia esos artistas.
    ids_recinto_como_artista: list = field(default_factory=list)


def distancia_km(a, b):
    """Distancia en línea recta entre dos puntos (latitud, longitud): fórmula de haversine."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def ciudad_mas_cercana(latitud, longitud, ciudades):
    """La ciudad cuyo radio contiene el punto; si caben varias, la más cercana."""
    dentro = []
    for ciudad in ciudades:
        km = distancia_km((latitud, longitud), (ciudad.latitud, ciudad.longitud))
        if km <= ciudad.radio_km:
            dentro.append((km, ciudad))
    return min(dentro, key=lambda par: par[0])[1] if dentro else None


def elegir_imagen(imagenes):
    """Prefiere 16:9 y un ancho cercano a 1024 px. Ignora las imágenes genéricas (fallback)."""
    utiles = [i for i in imagenes or [] if i.get("url") and not i.get("fallback")]
    if not utiles:
        return ""
    preferencia = {"16_9": 0, "3_2": 1, "4_3": 2}
    mejor = min(utiles, key=lambda i: (preferencia.get(i.get("ratio"), 3), abs((i.get("width") or 0) - ANCHO_IDEAL_IMAGEN)))
    return mejor["url"]


def traducir_genero(clasificaciones):
    nombre = ((clasificaciones or [{}])[0].get("genre") or {}).get("name", "")
    if nombre in GENEROS_SIN_DATO:
        return ""
    return GENEROS.get(nombre, nombre)


def leer_fecha(fechas):
    """Devuelve (fecha_hora con zona horaria, hora_por_confirmar)."""
    inicio = fechas.get("start") or {}
    hora_por_confirmar = bool(inicio.get("timeTBA") or inicio.get("noSpecificTime") or not inicio.get("localTime"))
    if inicio.get("dateTime"):
        return datetime.fromisoformat(inicio["dateTime"]), hora_por_confirmar
    if inicio.get("localDate"):
        # Sin hora: medianoche local de ese día, marcada como "por confirmar".
        zona = ZoneInfo(fechas.get("timezone") or ZONA_PREDETERMINADA)
        return datetime.combine(date.fromisoformat(inicio["localDate"]), time(), tzinfo=zona), True
    raise Descartado("sin_fecha")


def leer_precio(rangos):
    """El mínimo de todos los rangos de precio. Devuelve (precio o None, moneda)."""
    minimos = [(Decimal(str(r["min"])), r.get("currency") or "MXN") for r in rangos or [] if r.get("min") is not None]
    return min(minimos) if minimos else (None, "MXN")


def palabras(texto):
    """Las palabras del texto en minúsculas y sin acentos."""
    sin_acentos = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z0-9]+", sin_acentos))


def es_el_recinto(nombre_atraccion, nombre_recinto):
    """¿La "atracción" es en realidad el recinto? ("Sala Principal Bellas Artes" en "Palacio de Bellas Artes")."""
    atraccion, recinto = palabras(nombre_atraccion), palabras(nombre_recinto)
    if atraccion == recinto:
        return True
    distintivas = recinto - PALABRAS_DE_LUGAR - CONECTORES
    # Debe sonar a lugar ("sala", "teatro"...): así una banda como "Two Door Cinema Club" no cae.
    return (
        bool(distintivas)
        and bool(atraccion & PALABRAS_DE_LUGAR)
        and atraccion - PALABRAS_DE_LUGAR - CONECTORES == distintivas
    )


def limpiar_titulo(titulo):
    """Quita la edad mínima y la hora de ingreso del final del título."""
    return PATRON_COLA_DEL_TITULO.sub("", titulo).strip(" .,") or titulo


def artista_desde_titulo(titulo, ciudad):
    """Cuando Ticketmaster no dice quién toca, el título suele decirlo.

    "Akriila - El Tour de Lucy" -> "Akriila"; "Adanowsky en Monterrey" -> "Adanowsky".
    Sin id de Ticketmaster: el importador lo busca por nombre.
    """
    nombre = re.split(r"\s+[-–|]\s+", titulo)[0]
    nombre = re.sub(rf"\s+en\s+{re.escape(ciudad.nombre)}$", "", nombre, flags=re.IGNORECASE).strip()
    return DatosArtista(id_ticketmaster=None, nombre=(nombre or titulo)[:200], genero="", imagen_url="")


def traducir_artista(atraccion):
    return DatosArtista(
        id_ticketmaster=atraccion["id"],
        nombre=atraccion["name"].strip(),
        genero=traducir_genero(atraccion.get("classifications")),
        imagen_url=elegir_imagen(atraccion.get("images")),
    )


def traducir_evento(evento, ciudades):
    nombre = (evento.get("name") or "").strip()
    if PATRON_COMPLEMENTO.search(nombre):
        raise Descartado("complemento")
    if PATRON_PRUEBA.search(nombre):
        raise Descartado("prueba")
    if not evento.get("url"):
        raise Descartado("sin_enlace")

    incrustado = evento.get("_embedded") or {}
    recintos = incrustado.get("venues") or []
    if not recintos:
        raise Descartado("sin_recinto")
    recinto = recintos[0]
    ubicacion = recinto.get("location") or {}
    try:
        latitud, longitud = float(ubicacion["latitude"]), float(ubicacion["longitude"])
    except (KeyError, TypeError, ValueError):
        raise Descartado("sin_coordenadas")
    ciudad = ciudad_mas_cercana(latitud, longitud, ciudades)
    if ciudad is None:
        raise Descartado("fuera_de_ciudades")

    atracciones = [a for a in incrustado.get("attractions") or [] if a.get("id") and a.get("name")]
    nombre_recinto = recinto.get("name") or ""
    ids_recinto = [a["id"] for a in atracciones if es_el_recinto(a["name"], nombre_recinto)]
    artistas = [traducir_artista(a) for a in atracciones if a["id"] not in ids_recinto]
    if not artistas:
        # Sin atracciones, o solo el recinto: quién toca está en el título
        # ("Orquesta Sinfónica de Yucatán, CNMO. 8+. Ingreso 18:30 h.").
        nombre = limpiar_titulo(nombre)
        if not nombre:
            raise Descartado("sin_artista")
        artistas = [artista_desde_titulo(nombre, ciudad)]

    fecha_hora, hora_por_confirmar = leer_fecha(evento.get("dates") or {})
    precio, moneda = leer_precio(evento.get("priceRanges"))
    codigo_estado = ((evento.get("dates") or {}).get("status") or {}).get("code")

    return DatosConcierto(
        id_ticketmaster=evento["id"],
        titulo=nombre[:255],
        fecha_hora=fecha_hora,
        hora_por_confirmar=hora_por_confirmar,
        estado=ESTADOS.get(codigo_estado, Concierto.Estado.EN_VENTA),
        url_boletos=evento["url"],
        imagen_url=elegir_imagen(evento.get("images")),
        genero=traducir_genero(evento.get("classifications")) or artistas[0].genero,
        precio_desde=precio,
        moneda=moneda,
        recinto=DatosRecinto(
            id_ticketmaster=recinto["id"],
            nombre=(recinto.get("name") or "").strip(),
            direccion=((recinto.get("address") or {}).get("line1") or "").strip(),
            latitud=latitud,
            longitud=longitud,
            ciudad=ciudad,
        ),
        artista=artistas[0],
        invitados=artistas[1:],
        ids_recinto_como_artista=ids_recinto,
    )


def clave_de_grupo(datos):
    """Mismo artista, mismo recinto y mismo día local = el mismo concierto."""
    dia_local = datos.fecha_hora.astimezone(ZoneInfo(ZONA_PREDETERMINADA)).date()
    artista = datos.artista.id_ticketmaster or datos.artista.nombre.lower()
    return (artista, datos.recinto.id_ticketmaster, dia_local)


def agrupar(lista_datos):
    """Agrupa los eventos que son el mismo concierto, conservando el orden de llegada."""
    grupos = {}
    for datos in lista_datos:
        grupos.setdefault(clave_de_grupo(datos), []).append(datos)
    return list(grupos.values())


def fusionar(grupo):
    """Un solo concierto a partir de un grupo.

    Manda el evento que no es abono (y, entre iguales, el de id menor para que
    la elección sea estable de una noche a otra). Se queda con el precio más bajo.
    """
    principal = min(grupo, key=lambda d: (bool(PATRON_ABONO.match(d.titulo)), d.id_ticketmaster))
    precios = [d for d in grupo if d.precio_desde is not None]
    mas_barato = min(precios, key=lambda d: d.precio_desde) if precios else None
    return replace(
        principal,
        # "Abono General 3 días Corona Capital" no sirve de título: se usa el del artista.
        titulo=principal.artista.nombre if PATRON_ABONO.match(principal.titulo) else principal.titulo,
        imagen_url=principal.imagen_url or next((d.imagen_url for d in grupo if d.imagen_url), ""),
        precio_desde=mas_barato.precio_desde if mas_barato else None,
        moneda=mas_barato.moneda if mas_barato else principal.moneda,
    )
