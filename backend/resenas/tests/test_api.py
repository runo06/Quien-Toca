"""Listas de reseñas, promedios por artista y recinto, y la moderación en el panel."""
from django.contrib.admin.sites import site
from django.test import RequestFactory

from resenas.admin import ReporteAdmin
from resenas.models import Reporte, Resena, VotoUtil

from . import TEXTO, DatosDeResenas


class ListaYPromediosTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        crear = Resena.objects.create
        self.de_sofia = crear(usuario=self.sofia, concierto=self.pasado, general=5, show=5, sonido=4, recinto=3, texto=TEXTO, asistio=True)
        self.de_diego = crear(usuario=self.diego, concierto=self.pasado_gdl, general=2, sonido=2, texto=TEXTO, asistio=True)
        VotoUtil.objects.create(usuario=self.sofia, resena=self.de_diego)

    def test_lista_por_artista_con_las_mas_utiles_primero(self):
        datos = self.client.get("/api/resenas/", {"artista": self.cometas.slug}).data
        self.assertEqual([r["id"] for r in datos["resultados"]], [self.de_diego.pk, self.de_sofia.pk])
        self.assertEqual(datos["resultados"][0]["utiles"], 1)
        self.assertEqual(datos["resultados"][0]["concierto"]["ciudad"], "Guadalajara")

    def test_me_sirvio_y_es_mia_segun_quien_pregunta(self):
        self.como(self.sofia)
        resultados = self.client.get("/api/resenas/", {"artista": self.cometas.slug}).data["resultados"]
        por_id = {r["id"]: r for r in resultados}
        self.assertTrue(por_id[self.de_diego.pk]["me_sirvio"])
        self.assertFalse(por_id[self.de_diego.pk]["es_mia"])
        self.assertTrue(por_id[self.de_sofia.pk]["es_mia"])

    def test_filtra_por_concierto_y_por_ciudad(self):
        por_concierto = self.client.get("/api/resenas/", {"concierto": self.pasado.slug}).data
        self.assertEqual([r["id"] for r in por_concierto["resultados"]], [self.de_sofia.pk])
        por_ciudad = self.client.get("/api/resenas/", {"ciudad": "guadalajara"}).data
        self.assertEqual([r["id"] for r in por_ciudad["resultados"]], [self.de_diego.pk])

    def test_el_concierto_futuro_muestra_el_promedio_del_artista(self):
        datos = self.client.get(f"/api/conciertos/{self.futuro.slug}/").data
        self.assertEqual(
            datos["calificacion_artista"],
            {"promedio": 3.5, "total": 2, "show": 5.0, "sonido": 3.0, "puntualidad": None},
        )
        self.assertFalse(datos["se_puede_resenar"])
        # Las fechas pasadas del artista dicen cuántas reseñas tienen y si se pueden reseñar.
        pasadas = [f for f in datos["otras_fechas"] if f["ya_paso"]]
        self.assertEqual([(f["resenas"], f["se_puede_resenar"]) for f in pasadas], [(1, True), (1, True)])

    def test_promedio_del_recinto_solo_con_quien_lo_califico(self):
        datos = self.client.get(f"/api/conciertos/{self.futuro.slug}/").data
        self.assertEqual(datos["calificacion_recinto"], {"promedio": 3.0, "total": 1})  # Auditorio Nacional

    def test_la_cartelera_muestra_y_ordena_por_la_nota_del_artista(self):
        otro = self.concierto(self.auditorio, self.futuro.fecha_hora - self.futuro.fecha_hora.resolution)
        otro.artista = type(self.cometas).objects.create(nombre="Sin Reseñas")
        otro.save()
        datos = self.client.get("/api/conciertos/", {"orden": "nota"}).data["resultados"]
        self.assertEqual([c["slug"] for c in datos], [self.futuro.slug, otro.slug])
        self.assertEqual((datos[0]["promedio_artista"], datos[0]["resenas_artista"]), (3.5, 2))
        self.assertEqual((datos[1]["promedio_artista"], datos[1]["resenas_artista"]), (None, 0))

    def test_las_ocultas_no_se_ven_ni_cuentan(self):
        self.de_diego.oculta = True
        self.de_diego.save()
        datos = self.client.get("/api/resenas/", {"artista": self.cometas.slug}).data
        self.assertEqual([r["id"] for r in datos["resultados"]], [self.de_sofia.pk])
        detalle = self.client.get(f"/api/conciertos/{self.futuro.slug}/").data
        self.assertEqual(detalle["calificacion_artista"]["total"], 1)
        self.assertEqual(self.client.get(f"/api/resenas/{self.de_diego.pk}/").status_code, 404)

    def test_mis_resenas(self):
        self.como(self.sofia)
        self.assertEqual(self.client.get("/api/resenas/mias/").data, [{"id": self.de_sofia.pk, "concierto": self.pasado.slug}])

    def test_la_lista_no_hace_una_consulta_por_resena(self):
        with self.assertNumQueries(2):  # el conteo de la paginación y la página
            self.client.get("/api/resenas/", {"artista": self.cometas.slug})


class ModeracionTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        self.resena = Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=1, texto=TEXTO, asistio=True)
        self.reporte = Reporte.objects.create(resena=self.resena, usuario=self.diego, motivo="ofensiva")
        self.otro = Reporte.objects.create(
            resena=self.resena, usuario=type(self.diego).objects.create_user("ana@correo.mx"), motivo="spam"
        )
        self.admin = ReporteAdmin(Reporte, site)
        self.peticion = RequestFactory().post("/admin/")
        self.peticion._messages = type("Mensajes", (), {"add": lambda *a, **k: None})()

    def test_aceptar_oculta_la_resena_y_resuelve_sus_reportes(self):
        self.admin.aceptar(self.peticion, Reporte.objects.filter(pk=self.reporte.pk))
        self.resena.refresh_from_db()
        self.assertTrue(self.resena.oculta)
        self.assertEqual(set(Reporte.objects.values_list("estado", flat=True)), {Reporte.Estado.ACEPTADO})

    def test_descartar_deja_la_resena_visible(self):
        self.admin.descartar(self.peticion, Reporte.objects.filter(pk=self.reporte.pk))
        self.resena.refresh_from_db()
        self.assertFalse(self.resena.oculta)
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, Reporte.Estado.DESCARTADO)
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.estado, Reporte.Estado.PENDIENTE)
