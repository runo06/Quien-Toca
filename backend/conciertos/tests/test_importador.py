from datetime import datetime, time, timedelta, timezone as tz
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

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
        self.assertEqual(resumen.creados, 4)
        self.assertEqual(resumen.actualizados, 0)
        self.assertEqual(dict(resumen.descartados), {"complemento": 1, "fuera_de_ciudades": 1})
        self.assertEqual(resumen.errores, [])
        self.assertEqual(Concierto.objects.count(), 4)
        self.assertEqual(Recinto.objects.count(), 4)
        # Cometas, Marea Roja (invitada), Valentina, Niebla y Noche de Tributos (del título)
        self.assertEqual(Artista.objects.count(), 5)

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
        self.assertEqual(resumen.sin_cambios, 4)
        self.assertEqual(Concierto.objects.count(), 4)
        self.assertEqual(Recinto.objects.count(), 4)
        self.assertEqual(Artista.objects.count(), 5)

    def test_actualiza_lo_que_cambio_sin_cambiar_el_slug(self):
        importar(self.eventos)
        eventos = cargar_eventos()
        eventos[0]["dates"]["start"]["dateTime"] = "2026-11-22T03:00:00Z"
        eventos[0]["dates"]["status"]["code"] = "rescheduled"
        resumen = importar(eventos)
        self.assertEqual(resumen.actualizados, 1)
        self.assertEqual(resumen.sin_cambios, 3)
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

    def test_adopta_el_concierto_manual_del_mismo_dia_en_vez_de_duplicarlo(self):
        # Una sugerencia aprobada antes de que Ticketmaster lo publicara.
        cometas = Artista.objects.create(nombre="Los Cometas del Sur")
        auditorio = Recinto.objects.create(nombre="Auditorio Nacional", ciudad=Ciudad.objects.get(slug="cdmx"))
        manual = Concierto.objects.create(
            titulo="Los Cometas del Sur", artista=cometas, recinto=auditorio,
            fecha_hora=datetime(2026, 11, 20, 20, tzinfo=ZoneInfo("America/Mexico_City")), hora_por_confirmar=True,
            url_boletos="https://boletera.example/cometas",
        )

        resumen = importar(self.eventos)

        self.assertEqual(resumen.creados, 3)  # el de Cometas no se crea: se adopta
        self.assertEqual(Concierto.objects.filter(artista__nombre="Los Cometas del Sur").count(), 1)
        manual.refresh_from_db()
        self.assertEqual(manual.origen, Concierto.Origen.TICKETMASTER)
        self.assertEqual(manual.id_ticketmaster, "TM-COMETAS-CDMX")
        self.assertEqual(manual.titulo, "Los Cometas del Sur - Gira Polvo de Estrellas")
        self.assertFalse(manual.hora_por_confirmar)
        self.assertEqual(manual.slug, "los-cometas-del-sur-cdmx-2026-11-20")  # el enlace no cambia
        self.assertEqual(importar(cargar_eventos()).creados, 0)  # y otra noche ya lo reconoce por su id

    def test_vincula_artista_capturado_a_mano_en_vez_de_duplicarlo(self):
        manual = Artista.objects.create(nombre="los cometas del sur")
        importar(self.eventos)
        manual.refresh_from_db()
        self.assertEqual(manual.id_ticketmaster, "TM-A-COMETAS")
        self.assertEqual(Artista.objects.filter(nombre__iexact="los cometas del sur").count(), 1)

    def test_un_evento_con_error_no_detiene_a_los_demas(self):
        self.eventos[0]["url"] = "https://www.ticketmaster.com.mx/" + "a" * 600  # más largo que la columna
        resumen = importar(self.eventos)
        self.assertEqual(resumen.creados, 3)
        self.assertEqual(len(resumen.errores), 1)
        self.assertIn("TM-COMETAS-CDMX", resumen.errores[0])
        self.assertFalse(Concierto.objects.filter(id_ticketmaster="TM-COMETAS-CDMX").exists())


def abono(base, id_evento, nombre, precio=None):
    """Copia de un evento con otro id y nombre, como llegan los abonos de un festival."""
    evento = {**base, "id": id_evento, "name": nombre}
    if precio is not None:
        evento["priceRanges"] = [{"type": "standard", "currency": "MXN", "min": precio, "max": precio}]
    return evento


class AbonosTests(TestCase):
    def setUp(self):
        self.base = cargar_eventos()[0]  # Los Cometas del Sur, Auditorio Nacional, 20 de noviembre

    def test_abonos_del_mismo_dia_se_agrupan_con_el_concierto(self):
        eventos = [
            abono(self.base, "TM-ABONO-PLUS", "Abono Banamex Plus Los Cometas del Sur", precio=1500),
            self.base,
            abono(self.base, "TM-ABONO-GRAL", "Abono General Los Cometas del Sur", precio=900),
        ]
        resumen = importar(eventos)
        self.assertEqual(resumen.creados, 1)
        self.assertEqual(resumen.agrupados, 2)
        concierto = Concierto.objects.get()
        self.assertEqual(concierto.id_ticketmaster, "TM-COMETAS-CDMX")  # manda el que no es abono
        self.assertEqual(concierto.titulo, "Los Cometas del Sur - Gira Polvo de Estrellas")
        self.assertEqual(concierto.precio_desde, Decimal("900"))  # el más barato del grupo

    def test_festival_solo_con_abonos_usa_el_nombre_del_artista(self):
        eventos = [
            abono(self.base, "TM-ABONO-B", "Abono Comfort Pass Festival Cometas 2026"),
            abono(self.base, "TM-ABONO-A", "Abono General 3 días Festival Cometas 2026"),
        ]
        importar(eventos)
        concierto = Concierto.objects.get()
        self.assertEqual(concierto.id_ticketmaster, "TM-ABONO-A")  # entre abonos, el id menor
        self.assertEqual(concierto.titulo, "Los Cometas del Sur")

    def test_boletos_individuales_de_festival_se_agrupan(self):
        eventos = [
            abono(self.base, "TM-IND-B", "Individual Banamex Plus Corona Capital 2026", precio=2500),
            abono(self.base, "TM-IND-A", "Individual General Corona Capital 2026", precio=1800),
        ]
        resumen = importar(eventos)
        self.assertEqual((resumen.creados, resumen.agrupados), (1, 1))
        concierto = Concierto.objects.get()
        self.assertEqual(concierto.titulo, "Los Cometas del Sur")
        self.assertEqual(concierto.precio_desde, Decimal("1800"))

    def test_si_otra_noche_falta_el_principal_no_se_duplica(self):
        importar([self.base, abono(self.base, "TM-ABONO-GRAL", "Abono General Los Cometas del Sur")])
        resumen = importar([abono(self.base, "TM-ABONO-GRAL", "Abono General Los Cometas del Sur")])
        self.assertEqual(resumen.creados, 0)
        self.assertEqual(Concierto.objects.count(), 1)
        self.assertEqual(Concierto.objects.get().id_ticketmaster, "TM-COMETAS-CDMX")

    def test_abono_vip_sigue_siendo_complemento(self):
        resumen = importar([abono(self.base, "TM-ABONO-VIP", "Abono Banamex Stage Vip Time Warp")])
        self.assertEqual(dict(resumen.descartados), {"complemento": 1})

    def test_otro_dia_es_otro_concierto(self):
        otro_dia = abono(self.base, "TM-COMETAS-DIA2", "Los Cometas del Sur")
        otro_dia["dates"] = {**self.base["dates"], "start": {**self.base["dates"]["start"], "dateTime": "2026-11-22T03:00:00Z"}}
        self.assertEqual(importar([self.base, otro_dia]).creados, 2)


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
        self.assertIn("Creados: 4", texto)
        self.assertIn("Complementos (VIP, estacionamiento, meet & greet): 1", texto)
        cliente.eventos_por_meses.assert_called_once_with(12, countryCode="MX", classificationName="music")


class AtraccionQueEsElRecintoImportacionTests(TestCase):
    """Bellas Artes da de alta su sala como "artista" para toda su programación."""

    def funcion(self, id_evento, nombre, dia):
        evento = cargar_eventos()[0]  # en el Auditorio Nacional
        evento["id"] = id_evento
        evento["name"] = nombre
        evento["_embedded"]["attractions"] = [{"name": "Sala Principal Auditorio Nacional", "id": "TM-A-SALA"}]
        evento["dates"]["start"]["dateTime"] = f"2026-11-{dia}T02:00:00Z"
        return evento

    def test_cada_obra_es_su_propio_artista_sin_duplicarse(self):
        eventos = [
            self.funcion("TM-TOSCA-1", "Comp. Nal. Ópera Tosca de Giacomo Puccini, 10+. Ingreso 19:30 h.", 21),
            self.funcion("TM-TOSCA-2", "Comp. Nal. Ópera Tosca de Giacomo Puccini, 10+. Ingreso 16:30 h", 23),
            self.funcion("TM-ORQUESTA", "Orquesta Sinfónica de Yucatán, CNMO. 8+. Ingreso 18:30 h.", 25),
        ]
        importar(eventos)
        resumen = importar(eventos)  # otra noche: nada nuevo
        self.assertEqual(resumen.sin_cambios, 3)
        self.assertEqual(
            sorted(Artista.objects.values_list("nombre", flat=True)),
            ["Comp. Nal. Ópera Tosca de Giacomo Puccini", "Orquesta Sinfónica de Yucatán, CNMO"],
        )
        self.assertFalse(Artista.objects.filter(nombre__icontains="Sala Principal").exists())
        tosca = Artista.objects.get(nombre__startswith="Comp. Nal.")
        self.assertIsNone(tosca.id_ticketmaster)
        self.assertEqual(tosca.conciertos.count(), 2)

    def test_corrige_conciertos_importados_con_el_recinto_como_artista(self):
        importar([self.funcion("TM-TOSCA-1", "Comp. Nal. Ópera Tosca de Giacomo Puccini, 10+. Ingreso 19:30 h.", 21)])
        # Así quedaron antes del arreglo: el artista era la sala.
        sala = Artista.objects.create(nombre="Sala Principal Auditorio Nacional", id_ticketmaster="TM-A-SALA")
        Concierto.objects.update(artista=sala)
        resumen = importar([self.funcion("TM-TOSCA-1", "Comp. Nal. Ópera Tosca de Giacomo Puccini, 10+. Ingreso 19:30 h.", 21)])
        self.assertEqual(resumen.actualizados, 1)
        self.assertEqual(Concierto.objects.get().artista.nombre, "Comp. Nal. Ópera Tosca de Giacomo Puccini")
        self.assertFalse(Artista.objects.filter(pk=sala.pk).exists())  # ya sin conciertos, se borra

    def test_respeta_el_artista_corregido_a_mano(self):
        evento = self.funcion("TM-JEANETTE", "Jeanette Gira 50 Aniversario", 21)
        importar([evento])
        # En el panel se cambia el artista que salió del título por el correcto.
        jeanette = Artista.objects.create(nombre="Jeanette")
        Concierto.objects.update(artista=jeanette)
        resumen = importar([evento])
        self.assertEqual(resumen.sin_cambios, 1)
        self.assertEqual(Concierto.objects.get().artista, jeanette)

    def test_no_borra_al_recinto_como_artista_si_aun_tiene_conciertos(self):
        # Un concierto pasado que Ticketmaster ya no manda sigue apuntando a la sala.
        sala = Artista.objects.create(nombre="Sala Principal Auditorio Nacional", id_ticketmaster="TM-A-SALA")
        recinto = Recinto.objects.create(nombre="Auditorio Nacional", ciudad=Ciudad.objects.get(slug="cdmx"))
        Concierto.objects.create(
            titulo="Función pasada", artista=sala, recinto=recinto, url_boletos="https://x.mx",
            fecha_hora=timezone.now() - timedelta(days=30),
        )
        importar([self.funcion("TM-TOSCA-1", "Comp. Nal. Ópera Tosca de Giacomo Puccini, 10+. Ingreso 19:30 h.", 21)])
        self.assertTrue(Artista.objects.filter(pk=sala.pk).exists())
