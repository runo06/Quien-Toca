from datetime import timedelta

from django.utils import timezone

from conciertos.models import Artista, Concierto
from resenas.models import Resena
from resenas.tests import TEXTO, DatosDeResenas
from seguimiento.models import ArtistaSeguido, ConciertoGuardado


class SeguirYGuardarTests(DatosDeResenas):
    def test_seguir_y_dejar_de_seguir(self):
        self.como(self.sofia)
        url = f"/api/artistas/{self.cometas.slug}/seguir/"
        self.assertEqual(self.client.post(url).data, {"siguiendo": True, "seguidores": 1})
        self.assertEqual(self.client.post(url).data["seguidores"], 1)  # dos clics no cuentan doble
        detalle = self.client.get(f"/api/artistas/{self.cometas.slug}/").data
        self.assertEqual((detalle["siguiendo"], detalle["seguidores"]), (True, 1))
        self.assertEqual(self.client.delete(url).data, {"siguiendo": False, "seguidores": 0})

    def test_sin_sesion_no_se_sigue_y_la_pagina_dice_que_no(self):
        self.assertEqual(self.client.post(f"/api/artistas/{self.cometas.slug}/seguir/").status_code, 401)
        self.assertFalse(self.client.get(f"/api/artistas/{self.cometas.slug}/").data["siguiendo"])

    def test_guardar_un_concierto(self):
        self.como(self.sofia)
        url = f"/api/conciertos/{self.futuro.slug}/guardar/"
        self.assertEqual(self.client.post(url).data, {"guardado": True})
        self.assertTrue(self.client.get(f"/api/conciertos/{self.futuro.slug}/").data["guardado"])
        self.como(self.diego)  # lo que guarda Sofía no aparece guardado para Diego
        self.assertFalse(self.client.get(f"/api/conciertos/{self.futuro.slug}/").data["guardado"])
        self.como(self.sofia)
        self.assertEqual(self.client.delete(url).data, {"guardado": False})
        self.assertFalse(ConciertoGuardado.objects.exists())

    def test_concierto_inexistente(self):
        self.como(self.sofia)
        self.assertEqual(self.client.post("/api/conciertos/no-existe/guardar/").status_code, 404)


class MisConciertosTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        ahora = timezone.now()
        # Los Cometas también tocan pronto en Guadalajara, antes que en CDMX.
        self.futuro_gdl = self.concierto(self.estadio, ahora + timedelta(days=5))
        otro = Artista.objects.create(nombre="Marea Roja")
        self.no_seguido = Concierto.objects.create(
            titulo="Marea Roja", artista=otro, recinto=self.auditorio, fecha_hora=ahora + timedelta(days=2),
            url_boletos="https://boletos.mx",
        )
        ArtistaSeguido.objects.create(usuario=self.sofia, artista=self.cometas)
        ConciertoGuardado.objects.create(usuario=self.sofia, concierto=self.no_seguido)
        ConciertoGuardado.objects.create(usuario=self.sofia, concierto=self.pasado)
        ConciertoGuardado.objects.create(usuario=self.sofia, concierto=self.pasado_gdl)
        Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=5, texto=TEXTO, asistio=True)
        self.como(self.sofia)

    def test_mi_ciudad_primero(self):
        cdmx = self.client.get("/api/mis-conciertos/", {"ciudad": "cdmx"}).data
        self.assertEqual([c["slug"] for c in cdmx["de_artistas"]], [self.futuro.slug, self.futuro_gdl.slug])
        gdl = self.client.get("/api/mis-conciertos/", {"ciudad": "guadalajara"}).data
        self.assertEqual([c["slug"] for c in gdl["de_artistas"]], [self.futuro_gdl.slug, self.futuro.slug])

    def test_guardados_proximos_y_pasados_con_invitacion_a_resenar(self):
        datos = self.client.get("/api/mis-conciertos/").data
        self.assertEqual([c["slug"] for c in datos["guardados"]], [self.no_seguido.slug])
        pasados = {c["slug"]: c["resenaste"] for c in datos["guardados_pasados"]}
        self.assertEqual(pasados, {self.pasado.slug: True, self.pasado_gdl.slug: False})

    def test_artistas_que_sigo_con_sus_fechas(self):
        datos = self.client.get("/api/mis-conciertos/").data
        self.assertEqual([(a["nombre"], a["proximos"]) for a in datos["artistas"]], [("Los Cometas del Sur", 2)])

    def test_cada_quien_ve_lo_suyo(self):
        self.como(self.diego)
        datos = self.client.get("/api/mis-conciertos/").data
        self.assertEqual((datos["de_artistas"], datos["guardados"], datos["artistas"]), ([], [], []))

    def test_requiere_sesion(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/mis-conciertos/").status_code, 401)
