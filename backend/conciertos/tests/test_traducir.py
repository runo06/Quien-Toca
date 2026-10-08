from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from conciertos.importacion.traducir import (
    Descartado,
    artista_desde_titulo,
    ciudad_mas_cercana,
    elegir_imagen,
    es_el_recinto,
    limpiar_titulo,
    traducir_evento,
    traducir_genero,
)
from conciertos.models import Concierto

from . import cargar_eventos

# SimpleTestCase no usa base de datos: las ciudades son objetos simples con los mismos atributos.
CIUDADES = [
    SimpleNamespace(nombre="Ciudad de México", latitud=19.4326, longitud=-99.1332, radio_km=30),
    SimpleNamespace(nombre="Guadalajara", latitud=20.6597, longitud=-103.3496, radio_km=25),
    SimpleNamespace(nombre="Monterrey", latitud=25.6866, longitud=-100.3161, radio_km=25),
    SimpleNamespace(nombre="Puebla", latitud=19.0414, longitud=-98.2063, radio_km=20),
    SimpleNamespace(nombre="Tlaxcala", latitud=19.3139, longitud=-98.2404, radio_km=15),
]


class TraducirEventoTests(SimpleTestCase):
    def setUp(self):
        self.eventos = cargar_eventos()

    def test_evento_completo(self):
        datos = traducir_evento(self.eventos[0], CIUDADES)
        self.assertEqual(datos.id_ticketmaster, "TM-COMETAS-CDMX")
        self.assertEqual(datos.titulo, "Los Cometas del Sur - Gira Polvo de Estrellas")
        self.assertEqual(datos.fecha_hora, datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc))
        self.assertFalse(datos.hora_por_confirmar)
        self.assertEqual(datos.estado, Concierto.Estado.EN_VENTA)
        self.assertEqual(datos.genero, "Rock")
        self.assertIsNone(datos.precio_desde)
        self.assertEqual(datos.recinto.ciudad.nombre, "Ciudad de México")
        self.assertEqual(datos.recinto.direccion, "Paseo de la Reforma 50")
        self.assertEqual(datos.artista.nombre, "Los Cometas del Sur")
        self.assertEqual([a.nombre for a in datos.invitados], ["Marea Roja"])

    def test_imagen_ignora_fallback_y_prefiere_16_9_de_1024(self):
        datos = traducir_evento(self.eventos[0], CIUDADES)
        self.assertEqual(datos.imagen_url, "https://s1.ticketm.net/dam/a/cometas_16_9_1024.jpg")

    def test_recinto_en_zapopan_cuenta_como_guadalajara(self):
        datos = traducir_evento(self.eventos[1], CIUDADES)
        self.assertEqual(datos.recinto.ciudad.nombre, "Guadalajara")

    def test_sin_hora_queda_a_medianoche_local_y_por_confirmar(self):
        datos = traducir_evento(self.eventos[1], CIUDADES)
        self.assertTrue(datos.hora_por_confirmar)
        self.assertEqual(datos.fecha_hora, datetime(2026, 12, 5, tzinfo=ZoneInfo("America/Mexico_City")))
        self.assertEqual(datos.genero, "Baladas")

    def test_cancelado_con_precio_y_solo_imagen_generica(self):
        datos = traducir_evento(self.eventos[2], CIUDADES)
        self.assertEqual(datos.estado, Concierto.Estado.CANCELADO)
        self.assertEqual(datos.precio_desde, Decimal("450.0"))
        self.assertEqual(datos.moneda, "MXN")
        self.assertEqual(datos.imagen_url, "")
        self.assertEqual(datos.genero, "Electrónica")

    def test_descartes(self):
        for indice, motivo in [(3, "complemento"), (4, "fuera_de_ciudades")]:
            with self.subTest(motivo=motivo):
                with self.assertRaises(Descartado) as contexto:
                    traducir_evento(self.eventos[indice], CIUDADES)
                self.assertEqual(contexto.exception.motivo, motivo)

    def test_complementos_reales_vistos_en_ticketmaster(self):
        nombres = [
            "Aquihayaquihay VIP+MEET&GREET",
            "JIMMY SEA PRE-SIGNED POLAROID (Boleto de evento no incluido)",
            "JIMMY SEA - HI TOUCH JIMMY SEA (Boleto de evento no incluido)",
            "Andres Obregon M&G y Palomazo acustico",
            "NSQK MERCH UPGRADE (No da acceso al evento)",
            "Experiencia M&G con San Venus (sin boleto de evento)",
        ]
        for nombre in nombres:
            with self.subTest(nombre=nombre):
                evento = self.eventos[0]
                evento["name"] = nombre
                with self.assertRaises(Descartado):
                    traducir_evento(evento, CIUDADES)

    def test_abonos_e_individuales_no_son_complementos(self):
        for nombre in ["Abono General Time Warp", "Individual General Corona Capital 2026"]:
            with self.subTest(nombre=nombre):
                evento = self.eventos[0]
                evento["name"] = nombre
                self.assertEqual(traducir_evento(evento, CIUDADES).titulo, nombre)

    def test_descarta_recinto_sin_coordenadas(self):
        evento = self.eventos[0]
        del evento["_embedded"]["venues"][0]["location"]
        with self.assertRaises(Descartado) as contexto:
            traducir_evento(evento, CIUDADES)
        self.assertEqual(contexto.exception.motivo, "sin_coordenadas")

    def test_descarta_evento_sin_fecha(self):
        evento = self.eventos[0]
        evento["dates"]["start"] = {}
        with self.assertRaises(Descartado) as contexto:
            traducir_evento(evento, CIUDADES)
        self.assertEqual(contexto.exception.motivo, "sin_fecha")


class FuncionesAuxiliaresTests(SimpleTestCase):
    def test_entre_puebla_y_tlaxcala_gana_la_mas_cercana(self):
        self.assertEqual(ciudad_mas_cercana(19.30, -98.24, CIUDADES).nombre, "Tlaxcala")
        self.assertEqual(ciudad_mas_cercana(19.06, -98.22, CIUDADES).nombre, "Puebla")
        self.assertIsNone(ciudad_mas_cercana(20.97, -89.62, CIUDADES))

    def test_generos(self):
        self.assertEqual(traducir_genero([{"genre": {"name": "Latin"}}]), "Latino")
        self.assertEqual(traducir_genero([{"genre": {"name": "Undefined"}}]), "")
        self.assertEqual(traducir_genero([{"genre": {"name": "Polka"}}]), "Polka")
        self.assertEqual(traducir_genero([]), "")
        self.assertEqual(traducir_genero(None), "")

    def test_sin_imagenes_utiles(self):
        self.assertEqual(elegir_imagen(None), "")
        self.assertEqual(elegir_imagen([{"url": "https://x/f.jpg", "fallback": True}]), "")


def con_atraccion_del_recinto(evento, nombre, quedan_artistas=False):
    """Como llegan los eventos de Bellas Artes: la "atracción" es la sala del recinto."""
    sala = {"name": "Sala Principal Auditorio Nacional", "id": "TM-A-SALA", "classifications": [{"genre": {"name": "World"}}]}
    reales = evento["_embedded"]["attractions"] if quedan_artistas else []
    evento["_embedded"]["attractions"] = [sala, *reales]
    evento["name"] = nombre
    return evento


class AtraccionQueEsElRecintoTests(SimpleTestCase):
    def setUp(self):
        self.evento = cargar_eventos()[0]  # en el Auditorio Nacional

    def test_reconoce_al_recinto_disfrazado_de_artista(self):
        self.assertTrue(es_el_recinto("Sala Principal Bellas Artes", "Palacio de Bellas Artes"))
        self.assertTrue(es_el_recinto("Auditorio Nacional", "Auditorio Nacional"))
        # Bandas que no son el recinto, aunque su nombre suene a lugar o coincida en parte.
        self.assertFalse(es_el_recinto("Two Door Cinema Club", "Escenario GNP Seguros"))
        self.assertFalse(es_el_recinto("Los Ángeles Azules", "Teatro Metropólitan"))
        self.assertFalse(es_el_recinto("Bellas Artes", "Palacio de Bellas Artes Sala Manuel M. Ponce"))

    def test_solo_el_recinto_el_artista_sale_del_titulo(self):
        evento = con_atraccion_del_recinto(self.evento, "Comp. Nal. Ópera Tosca de Giacomo Puccini, 10+. Ingreso 19:30 h.")
        datos = traducir_evento(evento, CIUDADES)
        self.assertEqual(datos.artista.nombre, "Comp. Nal. Ópera Tosca de Giacomo Puccini")
        self.assertIsNone(datos.artista.id_ticketmaster)
        self.assertEqual(datos.titulo, "Comp. Nal. Ópera Tosca de Giacomo Puccini")
        self.assertEqual(datos.invitados, [])

    def test_si_hay_artistas_reales_se_ignora_el_recinto(self):
        evento = con_atraccion_del_recinto(self.evento, "Los Cometas del Sur en concierto", quedan_artistas=True)
        datos = traducir_evento(evento, CIUDADES)
        self.assertEqual(datos.artista.nombre, "Los Cometas del Sur")
        self.assertEqual([a.nombre for a in datos.invitados], ["Marea Roja"])
        self.assertEqual(datos.titulo, "Los Cometas del Sur en concierto")

    def test_sin_atracciones_el_artista_sale_del_titulo(self):
        datos = traducir_evento(cargar_eventos()[5], CIUDADES)
        self.assertEqual(datos.artista.nombre, "Noche de Tributos")
        self.assertIsNone(datos.artista.id_ticketmaster)
        self.assertEqual(datos.titulo, "Noche de Tributos")

    def test_artista_desde_titulo_quita_la_gira_y_la_ciudad(self):
        monterrey = CIUDADES[2]
        for titulo, artista in [
            ("Akriila - El Tour de Lucy", "Akriila"),
            ("Adanowsky en Monterrey", "Adanowsky"),
            ("Fernando Delgadillo y Alejandro Filio", "Fernando Delgadillo y Alejandro Filio"),
            ("Blink-182", "Blink-182"),
        ]:
            with self.subTest(titulo=titulo):
                self.assertEqual(artista_desde_titulo(titulo, monterrey).nombre, artista)

    def test_descarta_eventos_de_prueba(self):
        for nombre in ["Evento Demo Platinum HSBC", "EVENTO PRUEBA"]:
            evento = cargar_eventos()[5]
            evento["name"] = nombre
            with self.subTest(nombre=nombre):
                with self.assertRaises(Descartado) as contexto:
                    traducir_evento(evento, CIUDADES)
                self.assertEqual(contexto.exception.motivo, "prueba")

    def test_limpiar_titulo(self):
        self.assertEqual(limpiar_titulo("Orquesta Sinfónica de Yucatán, CNMO. 8+. Ingreso 18:30 h."), "Orquesta Sinfónica de Yucatán, CNMO")
        self.assertEqual(limpiar_titulo("Compañía Nacional de Danza Gala Balanchine, 6+. Ingreso 16:30 h"), "Compañía Nacional de Danza Gala Balanchine")
        self.assertEqual(limpiar_titulo("Blink-182"), "Blink-182")
        self.assertEqual(limpiar_titulo("Sum 41"), "Sum 41")


class EnlacesTests(SimpleTestCase):
    def test_guarda_el_primer_enlace_util_de_cada_tipo(self):
        from conciertos.importacion.traducir import leer_enlaces

        atraccion = {"externalLinks": {
            "instagram": [{"url": "https://www.instagram.com/rosanaoficial/"}, {"url": "https://otra"}],
            "itunes": [{"url": "https://music.apple.com/x"}],  # no se usa
            "musicbrainz": [{"id": "abc", "url": "https://musicbrainz.org/artist/abc"}],
            "homepage": [{"url": "javascript:alert(1)"}],  # solo http(s)
        }}
        self.assertEqual(leer_enlaces(atraccion), {
            "instagram": "https://www.instagram.com/rosanaoficial/",
            "musicbrainz": "https://musicbrainz.org/artist/abc",
        })
        self.assertEqual(leer_enlaces({}), {})
        # Solo la cuenta: se arma la dirección.
        arrobas = {"externalLinks": {"twitter": [{"url": "@_VicenteFdez"}], "facebook": [{"url": "@vicente"}]}}
        self.assertEqual(leer_enlaces(arrobas), {"twitter": "https://x.com/_VicenteFdez"})
