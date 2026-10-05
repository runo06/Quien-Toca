from datetime import datetime, timedelta, timezone as tz

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from conciertos.models import Artista, Ciudad, Concierto, Recinto


class CiudadesTests(TestCase):
    def test_la_migracion_crea_las_cinco_ciudades(self):
        self.assertEqual(
            set(Ciudad.objects.values_list("slug", flat=True)),
            {"cdmx", "guadalajara", "monterrey", "puebla", "tlaxcala"},
        )

    def test_solo_una_ciudad_predeterminada(self):
        self.assertEqual(Ciudad.objects.get(es_predeterminada=True).slug, "cdmx")
        with self.assertRaises(IntegrityError):
            Ciudad.objects.filter(slug="puebla").update(es_predeterminada=True)


class SlugTests(TestCase):
    def setUp(self):
        self.cdmx = Ciudad.objects.get(slug="cdmx")

    def test_slug_se_genera_y_no_se_repite(self):
        uno = Artista.objects.create(nombre="Marea Roja")
        dos = Artista.objects.create(nombre="Marea Roja")
        self.assertEqual(uno.slug, "marea-roja")
        self.assertEqual(dos.slug, "marea-roja-2")

    def test_slug_quita_acentos_y_signos(self):
        self.assertEqual(Artista.objects.create(nombre="¡Niebla Eléctrica!").slug, "niebla-electrica")

    def test_slug_de_concierto_usa_la_fecha_local(self):
        artista = Artista.objects.create(nombre="Los Cometas del Sur")
        recinto = Recinto.objects.create(nombre="Arena Central", ciudad=self.cdmx)
        # 03:00 UTC del 21 = 21:00 del 20 en la Ciudad de México.
        concierto = Concierto.objects.create(
            titulo="Los Cometas del Sur", artista=artista, recinto=recinto,
            fecha_hora=datetime(2026, 11, 21, 3, tzinfo=tz.utc), url_boletos="https://boletera.example/x",
        )
        self.assertEqual(concierto.slug, "los-cometas-del-sur-cdmx-2026-11-20")


class CamposTests(TestCase):
    def test_id_ticketmaster_vacio_se_guarda_como_nulo(self):
        cdmx = Ciudad.objects.get(slug="cdmx")
        uno = Recinto.objects.create(nombre="Foro Uno", ciudad=cdmx, id_ticketmaster="")
        Recinto.objects.create(nombre="Foro Dos", ciudad=cdmx, id_ticketmaster="")  # no choca con unique
        uno.refresh_from_db()
        self.assertIsNone(uno.id_ticketmaster)

    def test_concierto_nuevo_es_manual_y_sabe_si_ya_paso(self):
        cdmx = Ciudad.objects.get(slug="cdmx")
        concierto = Concierto.objects.create(
            titulo="Ayer", artista=Artista.objects.create(nombre="X"),
            recinto=Recinto.objects.create(nombre="Foro", ciudad=cdmx),
            fecha_hora=timezone.now() - timedelta(days=1), url_boletos="https://boletera.example/x",
        )
        self.assertEqual(concierto.origen, Concierto.Origen.MANUAL)
        self.assertTrue(concierto.ya_paso)
        self.assertEqual(concierto.ciudad, cdmx)
