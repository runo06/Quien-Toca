from datetime import datetime, time, timedelta, timezone as tz
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from conciertos.importacion.importador import Importador
from conciertos.models import Artista, Ciudad, Concierto, PrecioZona, Recinto

from . import cargar_eventos


def importar(eventos):
    return Importador().importar(eventos)


class ImportacionTests(TestCase):
    """Las ciudades vienen de la migración 0002, que también corre en la base de pruebas."""

    def setUp(self):
        self.eventos = cargar_eventos()

    def test_primera_importacion_crea_y_descarta(self):
        resumen = importar(self.eventos)
        self.assertEqual(resumen.creados, 3)
        self.assertEqual(resumen.actualizados, 0)
        self.assertEqual(dict(resumen.descartados), {"complemento": 1, "fuera_de_ciudades": 1, "sin_artista": 1})
        self.assertEqual(resumen.errores, [])
        self.assertEqual(Concierto.objects.count(), 3)
        self.assertEqual(Recinto.objects.count(), 3)
        self.assertEqual(Artista.objects.count(), 4)  # Cometas, Marea Roja (invitada), Valentina, Niebla

    def test_marca_el_origen_ticketmaster(self):
        importar(self.eventos)
        self.assertFalse(Concierto.objects.exclude(origen=Concierto.Origen.TICKETMASTER).exists())

    def test_guarda_relaciones_y_slug(self):
        importar(self.eventos)
        concierto = Concierto.objects.get(id_ticketmaster="TM-COMETAS-CDMX")
        self.assertEqual(concierto.artista.nombre, "Los Cometas del Sur")
        self.assertEqual([a.nombre for a in concierto.invitados.all()], ["Marea Roja"])
        self.assertEqual(concierto.ciudad.slug, "cdmx")
        self.assertEqual(concierto.slug, "los-cometas-del-sur-cdmx-2026-11-20")
        zapopan = Concierto.objects.get(id_ticketmaster="TM-VALENTINA-GDL")
        self.assertEqual(zapopan.ciudad.nombre, "Guadalajara")

    def test_segunda_importacion_no_duplica(self):
        importar(self.eventos)
        resumen = importar(cargar_eventos())
        self.assertEqual(resumen.creados, 0)
        self.assertEqual(resumen.sin_cambios, 3)
        self.assertEqual(Concierto.objects.count(), 3)
        self.assertEqual(Recinto.objects.count(), 3)
        self.assertEqual(Artista.objects.count(), 4)

    def test_actualiza_lo_que_cambio_sin_cambiar_el_slug(self):
        importar(self.eventos)
        eventos = cargar_eventos()
        eventos[0]["dates"]["start"]["dateTime"] = "2026-11-22T03:00:00Z"
        eventos[0]["dates"]["status"]["code"] = "rescheduled"
        resumen = importar(eventos)
        self.assertEqual(resumen.actualizados, 1)
        self.assertEqual(resumen.sin_cambios, 2)
        concierto = Concierto.objects.get(id_ticketmaster="TM-COMETAS-CDMX")
        self.assertEqual(concierto.fecha_hora, datetime(2026, 11, 22, 3, tzinfo=tz.utc))
        self.assertEqual(concierto.estado, Concierto.Estado.REPROGRAMADO)
        self.assertEqual(concierto.slug, "los-cometas-del-sur-cdmx-2026-11-20")  # el enlace compartido sigue sirviendo

    def test_actualiza_invitados(self):
        importar(self.eventos)
        eventos = cargar_eventos()
        del eventos[0]["_embedded"]["attractions"][1]
        self.assertEqual(importar(eventos).actualizados, 1)
        self.assertFalse(Concierto.objects.get(id_ticketmaster="TM-COMETAS-CDMX").invitados.exists())

    def test_conserva_campos_capturados_a_mano(self):
        importar(self.eventos)
        concierto = Concierto.objects.get(id_ticketmaster="TM-COMETAS-CDMX")
        concierto.gira = "Gira Polvo de Estrellas"
        concierto.apertura_puertas = time(19, 0)
        concierto.precio_desde = Decimal("780")
        concierto.save()
        PrecioZona.objects.create(concierto=concierto, zona="Pista", precio=Decimal("1720"))

        importar(cargar_eventos())

        concierto.refresh_from_db()
        self.assertEqual(concierto.gira, "Gira Polvo de Estrellas")
        self.assertEqual(concierto.apertura_puertas, time(19, 0))
        self.assertEqual(concierto.precio_desde, Decimal("780"))
        self.assertEqual(concierto.precios.count(), 1)

    def test_no_borra_conciertos_pasados(self):
        importar(self.eventos)
        concierto = Concierto.objects.get(id_ticketmaster="TM-NIEBLA-MTY")
        concierto.fecha_hora = timezone.now() - timedelta(days=30)
        concierto.save()
        sin_ese_evento = [e for e in cargar_eventos() if e["id"] != "TM-NIEBLA-MTY"]

        importar(sin_ese_evento)

        self.assertTrue(Concierto.objects.filter(id_ticketmaster="TM-NIEBLA-MTY").exists())

    def test_no_toca_los_conciertos_manuales(self):
        puebla = Ciudad.objects.get(slug="puebla")
        recinto = Recinto.objects.create(nombre="Auditorio del Valle", ciudad=puebla)
        artista = Artista.objects.create(nombre="Banda Sierra Madre")
        manual = Concierto.objects.create(
            titulo="Banda Sierra Madre 25 años", artista=artista, recinto=recinto,
            fecha_hora=datetime(2026, 12, 12, 1, tzinfo=tz.utc), url_boletos="https://boletera.example/sierra",
        )

        importar(self.eventos)

        manual.refresh_from_db()
        self.assertEqual(manual.origen, Concierto.Origen.MANUAL)
        self.assertEqual(manual.titulo, "Banda Sierra Madre 25 años")
        self.assertIsNone(manual.id_ticketmaster)

    def test_vincula_artista_capturado_a_mano_en_vez_de_duplicarlo(self):
        manual = Artista.objects.create(nombre="los cometas del sur")
        importar(self.eventos)
        manual.refresh_from_db()
        self.assertEqual(manual.id_ticketmaster, "TM-A-COMETAS")
        self.assertEqual(Artista.objects.filter(nombre__iexact="los cometas del sur").count(), 1)

    def test_un_evento_con_error_no_detiene_a_los_demas(self):
        self.eventos[0]["url"] = "https://www.ticketmaster.com.mx/" + "a" * 600  # más largo que la columna
        resumen = importar(self.eventos)
        self.assertEqual(resumen.creados, 2)
        self.assertEqual(len(resumen.errores), 1)
        self.assertIn("TM-COMETAS-CDMX", resumen.errores[0])
        self.assertFalse(Concierto.objects.filter(id_ticketmaster="TM-COMETAS-CDMX").exists())


class ComandoImportarTests(TestCase):
    @patch("conciertos.management.commands.importar_ticketmaster.ClienteTicketmaster")
    def test_comando_imprime_el_resumen(self, Cliente):
        # Se reemplaza el cliente por uno falso: la prueba no llama a la API real.
        cliente = Cliente.return_value
        cliente.eventos_por_meses.return_value = (cargar_eventos(), [])
        cliente.llamadas = 12
        salida = StringIO()

        call_command("importar_ticketmaster", stdout=salida)

        texto = salida.getvalue()
        self.assertIn("Eventos recibidos: 6 (12 llamadas a la API)", texto)
        self.assertIn("Creados: 3", texto)
        self.assertIn("Complementos (VIP, estacionamiento, abonos): 1", texto)
        cliente.eventos_por_meses.assert_called_once_with(12, countryCode="MX", classificationName="music")
