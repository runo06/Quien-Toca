"""Las reglas de quién puede reseñar, editar, borrar, votar y reportar."""
from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

from conciertos.models import Concierto
from resenas.models import Reporte, Resena, VotoUtil

from . import TEXTO, DatosDeResenas


class CrearResenaTests(DatosDeResenas):
    def test_sin_sesion_no_se_puede_resenar(self):
        self.assertEqual(self.resenar(self.pasado).status_code, 401)
        self.assertFalse(Resena.objects.exists())

    def test_resena_un_concierto_que_ya_paso(self):
        self.como(self.sofia)
        respuesta = self.resenar(self.pasado, show=5, sonido=4)
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(respuesta.data["autor"], "Sofía M.")
        self.assertTrue(respuesta.data["es_mia"])
        self.assertEqual(respuesta.data["concierto"]["slug"], self.pasado.slug)
        self.assertNotIn("asistio", respuesta.data)

    def test_nadie_resena_dos_veces_el_mismo_concierto(self):
        self.como(self.sofia)
        self.resenar(self.pasado)
        respuesta = self.resenar(self.pasado, general=1)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Ya reseñaste", str(respuesta.data["concierto"]))
        self.assertEqual(Resena.objects.count(), 1)

    def test_otra_fecha_del_mismo_artista_si_se_puede(self):
        self.como(self.sofia)
        self.resenar(self.pasado)
        self.assertEqual(self.resenar(self.pasado_gdl).status_code, 201)

    def test_la_base_tambien_impide_la_segunda_resena(self):
        Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=4, texto=TEXTO, asistio=True)
        with self.assertRaises(IntegrityError):
            Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=2, texto=TEXTO, asistio=True)

    def test_no_se_resena_un_concierto_futuro(self):
        self.como(self.sofia)
        respuesta = self.resenar(self.futuro)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("ya pasaron", str(respuesta.data["concierto"]))

    def test_no_se_resena_un_concierto_cancelado(self):
        cancelado = self.concierto(self.auditorio, timezone.now() - timedelta(days=1), estado=Concierto.Estado.CANCELADO)
        self.como(self.sofia)
        self.assertEqual(self.resenar(cancelado).status_code, 400)

    def test_hay_que_confirmar_que_asistio(self):
        self.como(self.sofia)
        for asistio in [False, None]:
            with self.subTest(asistio=asistio):
                datos = {} if asistio is None else {"asistio": asistio}
                respuesta = self.client.post(
                    "/api/resenas/", {"concierto": self.pasado.slug, "general": 5, "texto": TEXTO, **datos}, format="json"
                )
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("asistio", respuesta.data)

    def test_calificacion_general_obligatoria_y_de_1_a_5(self):
        self.como(self.sofia)
        for general in [None, 0, 6]:
            with self.subTest(general=general):
                datos = {"concierto": self.pasado.slug, "texto": TEXTO, "asistio": True}
                if general is not None:
                    datos["general"] = general
                respuesta = self.client.post("/api/resenas/", datos, format="json")
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("general", respuesta.data)

    def test_aspectos_opcionales_pero_de_1_a_5(self):
        self.como(self.sofia)
        self.assertEqual(self.resenar(self.pasado, sonido=9).status_code, 400)
        respuesta = self.resenar(self.pasado, show=None, sonido=3)
        self.assertEqual(respuesta.status_code, 201)
        self.assertIsNone(respuesta.data["show"])

    def test_comentario_de_al_menos_20_caracteres_sin_contar_espacios(self):
        self.como(self.sofia)
        respuesta = self.resenar(self.pasado, texto="   Muy bueno.             ")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("20 caracteres", str(respuesta.data["texto"]))


class EditarYBorrarTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        self.resena = Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=4, texto=TEXTO, asistio=True)
        self.url = f"/api/resenas/{self.resena.pk}/"

    def test_edita_su_propia_resena(self):
        self.como(self.sofia)
        respuesta = self.client.patch(self.url, {"general": 2, "texto": "Lo pensé mejor: el sonido falló bastante."}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.resena.refresh_from_db()
        self.assertEqual(self.resena.general, 2)
        self.assertIsNotNone(self.resena.editada)

    def test_nadie_edita_resenas_ajenas(self):
        self.como(self.diego)
        respuesta = self.client.patch(self.url, {"general": 1}, format="json")
        self.assertEqual(respuesta.status_code, 403)
        self.resena.refresh_from_db()
        self.assertEqual(self.resena.general, 4)

    def test_nadie_borra_resenas_ajenas(self):
        self.como(self.diego)
        self.assertEqual(self.client.delete(self.url).status_code, 403)
        self.assertTrue(Resena.objects.filter(pk=self.resena.pk).exists())

    def test_sin_sesion_no_se_edita_ni_borra(self):
        self.assertEqual(self.client.patch(self.url, {"general": 1}, format="json").status_code, 401)
        self.assertEqual(self.client.delete(self.url).status_code, 401)

    def test_al_editar_no_se_cambia_de_concierto(self):
        self.como(self.sofia)
        respuesta = self.client.patch(self.url, {"concierto": self.pasado_gdl.slug}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_al_editar_se_valida_el_texto(self):
        self.como(self.sofia)
        self.assertEqual(self.client.patch(self.url, {"texto": "corto"}, format="json").status_code, 400)

    def test_borra_su_propia_resena(self):
        self.como(self.sofia)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(Resena.objects.exists())
        # Ya borrada, puede volver a reseñar ese concierto.
        self.assertEqual(self.resenar(self.pasado).status_code, 201)


class MeSirvioYReportesTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        self.resena = Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=4, texto=TEXTO, asistio=True)

    def test_marcar_y_desmarcar_me_sirvio(self):
        self.como(self.diego)
        url = f"/api/resenas/{self.resena.pk}/util/"
        self.assertEqual(self.client.post(url).data, {"utiles": 1, "me_sirvio": True})
        self.assertEqual(self.client.post(url).data["utiles"], 1)  # dos clics no cuentan doble
        self.assertEqual(self.client.delete(url).data, {"utiles": 0, "me_sirvio": False})

    def test_no_se_vota_la_propia_resena(self):
        self.como(self.sofia)
        self.assertEqual(self.client.post(f"/api/resenas/{self.resena.pk}/util/").status_code, 403)
        self.assertFalse(VotoUtil.objects.exists())

    def test_votar_requiere_sesion(self):
        self.assertEqual(self.client.post(f"/api/resenas/{self.resena.pk}/util/").status_code, 401)

    def test_reportar_una_vez(self):
        self.como(self.diego)
        url = f"/api/resenas/{self.resena.pk}/reportar/"
        self.assertEqual(self.client.post(url, {"motivo": "spam"}).status_code, 201)
        segunda = self.client.post(url, {"motivo": "ofensiva"})
        self.assertEqual(segunda.status_code, 400)
        self.assertEqual(Reporte.objects.get().estado, Reporte.Estado.PENDIENTE)

    def test_reporte_con_motivo_valido(self):
        self.como(self.diego)
        self.assertEqual(self.client.post(f"/api/resenas/{self.resena.pk}/reportar/", {"motivo": "porque-si"}).status_code, 400)

    def test_no_se_reporta_la_propia_resena(self):
        self.como(self.sofia)
        self.assertEqual(self.client.post(f"/api/resenas/{self.resena.pk}/reportar/", {"motivo": "spam"}).status_code, 403)

    def test_una_resena_oculta_no_se_vota_ni_reporta(self):
        self.resena.oculta = True
        self.resena.save()
        self.como(self.diego)
        self.assertEqual(self.client.post(f"/api/resenas/{self.resena.pk}/util/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/resenas/{self.resena.pk}/reportar/", {"motivo": "spam"}).status_code, 404)
