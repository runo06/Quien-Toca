"""Traduce un evento de Ticketmaster a los datos de ¿Quién toca?

No toca la base de datos ni la red: recibe el diccionario del evento y las
ciudades, y devuelve un DatosConcierto o lanza Descartado con el motivo.
"""
import math
import re
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


class Descartado(Exception):
    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


@dataclass(frozen=True)
class DatosArtista:
    id_ticketmaster: str
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

    artistas = [traducir_artista(a) for a in incrustado.get("attractions") or [] if a.get("id") and a.get("name")]
    if not artistas:
        raise Descartado("sin_artista")

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
    )


def clave_de_grupo(datos):
    """Mismo artista, mismo recinto y mismo día local = el mismo concierto."""
    dia_local = datos.fecha_hora.astimezone(ZoneInfo(ZONA_PREDETERMINADA)).date()
    return (datos.artista.id_ticketmaster, datos.recinto.id_ticketmaster, dia_local)


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
