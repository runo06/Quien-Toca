from datetime import date, time, timedelta

from django.core.cache import cache
from django.utils import timezone

from conciertos.models import Artista, Concierto, Recinto
from resenas.tests import DatosDeResenas
from sugerencias.aprobar import aprobar, rechazar
from sugerencias.models import Sugerencia


class SugerirTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        cache.clear()  # el freno de 20 por día vive en la caché
        self.manana = timezone.localdate() + timedelta(days=1)

    def sugerir(self, **campos):
        datos = {
            "artista": "Café Tacvba", "ciudad": "cdmx", "recinto": "Auditorio Nacional",
            "fecha": self.manana.isoformat(), "hora": "21:00", "url_boletos": "https://boletos.mx/tacvba", **campos,
        }
        return self.client.post("/api/sugerencias/", datos, format="json")

    def test_sugerir_queda_pendiente(self):
        self.como(self.sofia)
        respuesta = self.sugerir()
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(respuesta.data["estado"], "pendiente")
        self.assertEqual(Sugerencia.objects.get().usuario, self.sofia)
        self.assertEqual(Concierto.objects.filter(artista__nombre="Café Tacvba").count(), 0)  # aún no se crea

    def test_requiere_sesion(self):
        self.assertEqual(self.sugerir().status_code, 401)

    def test_no_se_sugiere_un_dia_que_ya_paso(self):
        self.como(self.sofia)
        respuesta = self.sugerir(fecha=(timezone.localdate() - timedelta(days=1)).isoformat())
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("fecha", respuesta.data)

    def test_campos_obligatorios(self):
        self.como(self.sofia)
        respuesta = self.client.post("/api/sugerencias/", {}, format="json")
        self.assertEqual(set(respuesta.data), {"artista", "ciudad", "recinto", "fecha", "url_boletos"})

    def test_cada_quien_ve_sus_sugerencias(self):
        self.como(self.sofia)
        self.sugerir()
        self.assertEqual(len(self.client.get("/api/sugerencias/").data), 1)
        self.como(self.diego)
        self.assertEqual(self.client.get("/api/sugerencias/").data, [])

    def test_frena_el_exceso(self):
        self.como(self.sofia)
        codigos = [self.sugerir(artista=f"Banda {n}").status_code for n in range(21)]
        self.assertEqual(codigos[-1], 429)


class AprobarTests(DatosDeResenas):
    def sugerencia(self, **campos):
        datos = {
            "usuario": self.sofia, "artista": "cafe tacvba", "ciudad": self.auditorio.ciudad, "recinto": "auditorio nacional",
            "fecha": date(2026, 12, 12), "hora": time(21, 0), "url_boletos": "https://boletos.mx/tacvba", **campos,
        }
        return Sugerencia.objects.create(**datos)

    def test_aprobar_crea_el_concierto_reusando_artista_y_recinto(self):
        tacvba = Artista.objects.create(nombre="Café Tacvba")
        sugerencia = self.sugerencia()
        concierto = aprobar(sugerencia)
        self.assertEqual(concierto.artista, tacvba)  # sin importar acentos ni mayúsculas
        self.assertEqual(concierto.recinto, self.auditorio)
        self.assertEqual(concierto.origen, Concierto.Origen.MANUAL)
        self.assertEqual(concierto.slug, "cafe-tacvba-cdmx-2026-12-12")  # el día en hora de México
        self.assertFalse(concierto.hora_por_confirmar)
        sugerencia.refresh_from_db()
        self.assertEqual((sugerencia.estado, sugerencia.concierto), (Sugerencia.Estado.APROBADA, concierto))

    def test_sin_hora_queda_por_confirmar_y_crea_lo_que_falta(self):
        concierto = aprobar(self.sugerencia(hora=None, recinto="Foro Nuevo", artista="Banda Nueva"))
        self.assertTrue(concierto.hora_por_confirmar)
        self.assertTrue(Recinto.objects.filter(nombre="Foro Nuevo", ciudad=self.auditorio.ciudad).exists())
        self.assertTrue(Artista.objects.filter(nombre="Banda Nueva").exists())

    def test_si_el_concierto_ya_existe_no_se_duplica(self):
        # Llegó de Ticketmaster mientras la sugerencia esperaba.
        existente = self.concierto(self.auditorio, self.futuro.fecha_hora + timedelta(days=60))
        sugerencia = self.sugerencia(artista="Los Cometas del Sur", fecha=timezone.localtime(existente.fecha_hora).date())
        self.assertEqual(aprobar(sugerencia), existente)

    def test_aprobar_dos_veces_no_crea_dos(self):
        sugerencia = self.sugerencia()
        self.assertEqual(aprobar(sugerencia), aprobar(sugerencia))
        self.assertEqual(Concierto.objects.filter(artista__nombre="cafe tacvba").count(), 1)

    def test_rechazar_con_motivo(self):
        sugerencia = self.sugerencia()
        rechazar(sugerencia, "Ese concierto es en 2027.")
        sugerencia.refresh_from_db()
        self.assertEqual((sugerencia.estado, sugerencia.motivo_rechazo), ("rechazada", "Ese concierto es en 2027."))
        self.assertIsNone(sugerencia.concierto)
