"""Funciones puras para medir qué tan completos vienen los eventos.

No hacen llamadas de red: reciben eventos (diccionarios tal como los entrega
la API) y devuelven números. Por eso se pueden probar sin clave.
"""
import math
import re
import unicodedata
from collections import Counter, defaultdict

OTRAS = "Otras ciudades"

# Cada ciudad es su zona metropolitana: muchos recintos grandes están en el
# municipio vecino (Estadio Akron en Zapopan, Estadio BBVA en Guadalupe, etc.).
# Se usa la distancia al centro cuando el recinto trae coordenadas; si no, el nombre.
CIUDADES = {
    "Puebla": {
        "centro": (19.0414, -98.2063),
        "radio_km": 20,
        "nombres": {"puebla", "heroica puebla de zaragoza", "san andres cholula", "san pedro cholula", "cholula"},
    },
    "Tlaxcala": {
        "centro": (19.3139, -98.2404),
        "radio_km": 15,
        "nombres": {"tlaxcala", "tlaxcala de xicohtencatl"},
    },
    "Ciudad de México": {
        "centro": (19.4326, -99.1332),
        "radio_km": 30,
        "nombres": {"ciudad de mexico", "mexico city", "cdmx", "mexico d f", "distrito federal"},
    },
    "Guadalajara": {
        "centro": (20.6597, -103.3496),
        "radio_km": 25,
        "nombres": {"guadalajara", "zapopan", "tlaquepaque", "san pedro tlaquepaque", "tonala", "tlajomulco de zuniga"},
    },
    "Monterrey": {
        "centro": (25.6866, -100.3161),
        "radio_km": 25,
        "nombres": {"monterrey", "san pedro garza garcia", "guadalupe", "san nicolas de los garza", "apodaca", "santa catarina"},
    },
}

# Campos que nos interesan: (ruta dentro del JSON, para qué nos serviría).
CAMPOS = [
    ("id", "Identificador del evento"),
    ("name", "Nombre del evento"),
    ("url", "Enlace a la boletera"),
    ("dates.start.localDate", "Fecha local"),
    ("dates.start.localTime", "Hora local"),
    ("dates.start.dateTime", "Fecha y hora UTC"),
    ("dates.timezone", "Zona horaria"),
    ("dates.status.code", "Estado (en venta, cancelado...)"),
    ("sales.public.startDateTime", "Inicio de venta al público"),
    ("priceRanges.0.min", "Precio mínimo"),
    ("priceRanges.0.max", "Precio máximo"),
    ("priceRanges.0.currency", "Moneda"),
    ("images", "Imágenes del evento"),
    ("classifications.0.genre.name", "Género"),
    ("classifications.0.subGenre.name", "Subgénero"),
    ("info", "Información adicional"),
    ("pleaseNote", "Avisos"),
    ("promoter.name", "Promotor"),
    ("seatmap.staticUrl", "Mapa de zonas"),
    ("_embedded.venues.0.id", "Recinto: id"),
    ("_embedded.venues.0.name", "Recinto: nombre"),
    ("_embedded.venues.0.address.line1", "Recinto: dirección"),
    ("_embedded.venues.0.city.name", "Recinto: ciudad"),
    ("_embedded.venues.0.state.name", "Recinto: estado"),
    ("_embedded.venues.0.postalCode", "Recinto: código postal"),
    ("_embedded.venues.0.location.latitude", "Recinto: coordenadas"),
    ("_embedded.venues.0.images", "Recinto: imágenes"),
    ("_embedded.venues.0.boxOfficeInfo", "Recinto: taquilla"),
    ("_embedded.venues.0.parkingDetail", "Recinto: estacionamiento"),
    ("_embedded.attractions.0.id", "Artista: id"),
    ("_embedded.attractions.0.name", "Artista: nombre"),
    ("_embedded.attractions.0.images", "Artista: imágenes"),
    ("_embedded.attractions.0.classifications.0.genre.name", "Artista: género"),
    ("_embedded.attractions.0.externalLinks", "Artista: redes y enlaces"),
]

# Eventos que no son el concierto en sí, sino un producto aparte (estacionamiento, paquetes VIP).
PATRON_COMPLEMENTO = re.compile(
    r"estacionamiento|parking|paquete|\bvip\b|hospitality|experiencia|upgrade|souvenir|merch",
    re.IGNORECASE,
)
PATRON_PUERTAS = re.compile(r"puertas|doors", re.IGNORECASE)
PATRON_GIRA = re.compile(r"\b(tour|gira)\b", re.IGNORECASE)


def normalizar(texto):
    """'Ciudad de México' -> 'ciudad de mexico': sin acentos, signos ni mayúsculas."""
    sin_acentos = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^\w\s]", " ", sin_acentos.lower()).split())


def obtener(dato, ruta):
    """Lee una ruta como 'priceRanges.0.min'; devuelve None si algo falta en el camino."""
    for parte in ruta.split("."):
        if isinstance(dato, dict):
            dato = dato.get(parte)
        elif isinstance(dato, list) and parte.isdigit() and int(parte) < len(dato):
            dato = dato[int(parte)]
        else:
            return None
    return dato


def tiene(dato, ruta):
    """True si la ruta existe y no está vacía. Un 0 sí cuenta como dato."""
    return obtener(dato, ruta) not in (None, "", [], {})


def distancia_km(a, b):
    """Distancia en línea recta entre dos puntos (latitud, longitud): fórmula de haversine."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def ciudad_de_evento(evento):
    """Devuelve la ciudad del proyecto a la que pertenece el evento, o None."""
    recinto = obtener(evento, "_embedded.venues.0") or {}
    latitud, longitud = obtener(recinto, "location.latitude"), obtener(recinto, "location.longitude")
    if latitud and longitud:
        punto = (float(latitud), float(longitud))
        distancias = {nombre: distancia_km(punto, datos["centro"]) for nombre, datos in CIUDADES.items()}
        dentro = [nombre for nombre, km in distancias.items() if km <= CIUDADES[nombre]["radio_km"]]
        # Puebla y Tlaxcala están a 30 km: si un punto cae en ambas, gana la más cercana.
        return min(dentro, key=distancias.get) if dentro else None
    nombre = normalizar(obtener(recinto, "city.name"))
    for ciudad, datos in CIUDADES.items():
        if nombre in datos["nombres"]:
            return ciudad
    return None


def contar_por_ciudad(eventos):
    conteo = Counter({ciudad: 0 for ciudad in [*CIUDADES, OTRAS]})
    conteo.update(ciudad_de_evento(e) or OTRAS for e in eventos)
    return conteo


def nombres_reportados(eventos):
    """Qué nombres de ciudad trae Ticketmaster dentro de cada una de nuestras ciudades."""
    nombres = defaultdict(Counter)
    for evento in eventos:
        nombre = obtener(evento, "_embedded.venues.0.city.name") or "(sin ciudad)"
        nombres[ciudad_de_evento(evento) or OTRAS][nombre] += 1
    return nombres


def cobertura(eventos, campos=CAMPOS):
    """Lista de (ruta, descripción, cuántos lo traen, porcentaje)."""
    total = len(eventos)
    resultado = []
    for ruta, descripcion in campos:
        presentes = sum(tiene(e, ruta) for e in eventos)
        resultado.append((ruta, descripcion, presentes, 100 * presentes / total if total else 0.0))
    return resultado


def posibles_complementos(eventos):
    return [e for e in eventos if PATRON_COMPLEMENTO.search(e.get("name", ""))]


def posibles_duplicados(eventos):
    """Grupos con el mismo artista, recinto y día. Pueden ser dobles funciones o repetidos."""
    grupos = defaultdict(list)
    for evento in eventos:
        clave = (
            obtener(evento, "_embedded.attractions.0.id") or normalizar(evento.get("name")),
            obtener(evento, "_embedded.venues.0.id"),
            obtener(evento, "dates.start.localDate"),
        )
        grupos[clave].append(evento)
    return [grupo for grupo in grupos.values() if len(grupo) > 1]


def menciona_puertas(evento):
    return any(PATRON_PUERTAS.search(evento.get(campo) or "") for campo in ("info", "pleaseNote", "additionalInfo"))


def menciona_gira(evento):
    return bool(PATRON_GIRA.search(evento.get("name", "")))


def resumen_imagenes(eventos):
    proporciones, con_atribucion, anchos = Counter(), 0, []
    for evento in eventos:
        imagenes = evento.get("images") or []
        proporciones.update(imagen.get("ratio", "?") for imagen in imagenes)
        con_atribucion += any(imagen.get("attribution") for imagen in imagenes)
        anchos += [imagen.get("width", 0) for imagen in imagenes]
    return {"proporciones": proporciones, "con_atribucion": con_atribucion, "ancho_maximo": max(anchos, default=0)}


def elegir_ejemplo(eventos):
    """El evento con más campos llenos: el mejor caso para ver la estructura completa."""
    return max(eventos, key=lambda e: sum(tiene(e, ruta) for ruta, _ in CAMPOS), default=None)
