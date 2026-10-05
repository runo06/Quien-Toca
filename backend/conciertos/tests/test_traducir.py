from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from conciertos.importacion.traducir import (
    Descartado,
    ciudad_mas_cercana,
    elegir_imagen,
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
        for indice, motivo in [(3, "complemento"), (4, "fuera_de_ciudades"), (5, "sin_artista")]:
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
