from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group

from conciertos.models import Artista, Concierto
from edicion.roles import GRUPO_EDITORES
from resenas.models import Reporte, Resena
from resenas.tests import TEXTO, DatosDeResenas
from sugerencias.models import Sugerencia

MEXICO = ZoneInfo("America/Mexico_City")


class EdicionTests(DatosDeResenas):
    def setUp(self):
        super().setUp()
        self.editora = type(self.sofia).objects.create_user("eva@correo.mx", "eva@correo.mx", "clave-larga-3", first_name="Eva")
        self.editora.groups.add(Group.objects.get(name=GRUPO_EDITORES))  # el grupo lo crea una migración

    def gira(self, **cambios):
        datos = {
            "artista": self.cometas.pk, "gira": "Polvo de Estrellas", "url_boletos": "https://boletos.mx/cometas",
            "fechas": [
                {"recinto": self.auditorio.pk, "fecha": "2027-02-10", "hora": "21:00"},
                {"recinto": self.estadio.pk, "fecha": "2027-02-12", "precio_desde": "450"},
            ],
            **cambios,
        }
        return self.client.post("/api/edicion/giras/", datos, format="json")


class PermisosTests(EdicionTests):
    RUTAS = ["/api/edicion/", "/api/edicion/artistas/?q=co", "/api/edicion/sugerencias/", "/api/edicion/reportes/"]

    def test_solo_editores(self):
        for ruta in self.RUTAS:
            with self.subTest(ruta=ruta):
                self.client.force_authenticate(None)
                self.assertEqual(self.client.get(ruta).status_code, 401)
                self.como(self.sofia)  # con cuenta, pero sin el rol
                self.assertEqual(self.client.get(ruta).status_code, 403)
                self.como(self.editora)
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_sin_rol_no_crea_ni_edita(self):
        self.como(self.sofia)
        self.assertEqual(self.gira().status_code, 403)
        respuesta = self.client.patch(f"/api/edicion/conciertos/{self.futuro.slug}/", {"estado": "cancelado"}, format="json")
        self.assertEqual(respuesta.status_code, 403)
        self.futuro.refresh_from_db()
        self.assertEqual(self.futuro.estado, Concierto.Estado.EN_VENTA)

    def test_la_cuenta_dice_si_es_editor(self):
        self.como(self.editora)
        self.assertTrue(self.client.get("/api/cuentas/yo/").data["es_editor"])
        self.como(self.sofia)
        self.assertFalse(self.client.get("/api/cuentas/yo/").data["es_editor"])


class CapturaTests(EdicionTests):
    def setUp(self):
        super().setUp()
        self.como(self.editora)

    def test_buscar_y_dar_de_alta_artistas_y_recintos(self):
        self.assertEqual([a["nombre"] for a in self.client.get("/api/edicion/artistas/", {"q": "cometas"}).data], ["Los Cometas del Sur"])
        nuevo = self.client.post("/api/edicion/artistas/", {"nombre": "Banda Nueva"}, format="json")
        self.assertEqual(nuevo.status_code, 201)
        repetido = self.client.post("/api/edicion/artistas/", {"nombre": "banda nueva"}, format="json")
        self.assertEqual((repetido.status_code, repetido.data["id"]), (200, nuevo.data["id"]))  # no se duplica
        recintos = self.client.get("/api/edicion/recintos/", {"q": "audit", "ciudad": "cdmx"}).data
        self.assertEqual([(r["nombre"], r["ciudad_nombre"]) for r in recintos], [("Auditorio Nacional", "Ciudad de México")])
        foro = self.client.post("/api/edicion/recintos/", {"nombre": "Foro Nuevo", "ciudad": "puebla"}, format="json")
        self.assertEqual((foro.status_code, foro.data["ciudad"]), (201, "puebla"))

    def test_capturar_una_gira(self):
        respuesta = self.gira()
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(len(respuesta.data), 2)
        cdmx = Concierto.objects.get(fecha_hora=datetime(2027, 2, 10, 21, tzinfo=MEXICO))
        self.assertEqual((cdmx.gira, cdmx.origen, cdmx.hora_por_confirmar), ("Polvo de Estrellas", "manual", False))
        gdl = Concierto.objects.get(recinto=self.estadio, fecha_hora__date=date(2027, 2, 12))
        self.assertTrue(gdl.hora_por_confirmar)
        self.assertEqual(gdl.precio_desde, 450)

    def test_gira_con_una_fecha_que_ya_existe_no_crea_ninguna(self):
        antes = Concierto.objects.count()
        dia = self.futuro.fecha_hora.astimezone(MEXICO).date().isoformat()
        respuesta = self.gira(fechas=[
            {"recinto": self.estadio.pk, "fecha": "2027-02-12"},
            {"recinto": self.auditorio.pk, "fecha": dia},
        ])
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["fechas"][0], {})
        self.assertIn("Ya existe", str(respuesta.data["fechas"][1]["fecha"]))
        self.assertEqual(Concierto.objects.count(), antes)

    def test_gira_sin_fechas(self):
        self.assertEqual(self.gira(fechas=[]).status_code, 400)

    def test_editar_y_cancelar_un_concierto_manual(self):
        url = f"/api/edicion/conciertos/{self.futuro.slug}/"
        respuesta = self.client.patch(url, {"fecha": "2027-03-01", "hora": None, "estado": "pospuesto", "precio_desde": "999"}, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.futuro.refresh_from_db()
        self.assertEqual(self.futuro.fecha_hora, datetime(2027, 3, 1, tzinfo=MEXICO))
        self.assertTrue(self.futuro.hora_por_confirmar)
        self.assertEqual(self.futuro.estado, "pospuesto")
        self.client.patch(url, {"hora": "20:30"}, format="json")  # solo la hora: el día se conserva
        self.futuro.refresh_from_db()
        self.assertEqual(self.futuro.fecha_hora, datetime(2027, 3, 1, 20, 30, tzinfo=MEXICO))

    def test_en_uno_de_ticketmaster_solo_lo_que_no_se_importa(self):
        self.futuro.origen = Concierto.Origen.TICKETMASTER
        self.futuro.save()
        url = f"/api/edicion/conciertos/{self.futuro.slug}/"
        self.assertIn("estado", self.client.get(url).data["campos_bloqueados"])
        bloqueado = self.client.patch(url, {"estado": "cancelado"}, format="json")
        self.assertEqual(bloqueado.status_code, 400)
        self.assertIn("Ticketmaster", str(bloqueado.data["estado"]))
        permitido = self.client.patch(url, {"gira": "Gira 2027", "apertura_puertas": "19:00"}, format="json")
        self.assertEqual(permitido.status_code, 200)


class RevisionTests(EdicionTests):
    def setUp(self):
        super().setUp()
        self.como(self.editora)

    def test_aprobar_sugerencia_corrigiendo_el_nombre(self):
        tacvba = Artista.objects.create(nombre="Café Tacvba")
        sugerencia = Sugerencia.objects.create(
            usuario=self.sofia, artista="cafe tacuba", ciudad=self.auditorio.ciudad, recinto="Auditorio Nacional",
            fecha=date(2027, 1, 20), hora=time(21), url_boletos="https://boletos.mx",
        )
        self.assertEqual([s["id"] for s in self.client.get("/api/edicion/sugerencias/").data], [sugerencia.pk])
        respuesta = self.client.post(f"/api/edicion/sugerencias/{sugerencia.pk}/aprobar/", {"artista": "Café Tacvba"}, format="json")
        self.assertEqual(respuesta.data["estado"], "aprobada")
        self.assertEqual(Concierto.objects.get(slug=respuesta.data["concierto"]).artista, tacvba)
        otra_vez = self.client.post(f"/api/edicion/sugerencias/{sugerencia.pk}/rechazar/", {"motivo": "x"}, format="json")
        self.assertEqual(otra_vez.status_code, 400)  # ya se revisó
        self.assertEqual(self.client.get("/api/edicion/sugerencias/").data, [])  # ya no está pendiente

    def test_rechazar_sugerencia(self):
        sugerencia = Sugerencia.objects.create(
            usuario=self.sofia, artista="X", ciudad=self.auditorio.ciudad, recinto="Y",
            fecha=date(2027, 1, 20), url_boletos="https://boletos.mx",
        )
        self.client.post(f"/api/edicion/sugerencias/{sugerencia.pk}/rechazar/", {"motivo": "No encontramos ese concierto."}, format="json")
        sugerencia.refresh_from_db()
        self.assertEqual((sugerencia.estado, sugerencia.motivo_rechazo), ("rechazada", "No encontramos ese concierto."))

    def test_moderar_reportes(self):
        resena = Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=1, texto=TEXTO, asistio=True)
        uno = Reporte.objects.create(resena=resena, usuario=self.diego, motivo="ofensiva")
        Reporte.objects.create(resena=resena, usuario=self.editora, motivo="spam")
        lista = self.client.get("/api/edicion/reportes/").data
        self.assertEqual((len(lista), lista[0]["reportes_de_la_resena"], lista[0]["texto"]), (2, 2, TEXTO))
        self.assertEqual(self.client.get("/api/edicion/").data, {"sugerencias_pendientes": 0, "reportes_pendientes": 2})
        self.client.post(f"/api/edicion/reportes/{uno.pk}/aceptar/")
        resena.refresh_from_db()
        self.assertTrue(resena.oculta)
        self.assertEqual(self.client.get("/api/edicion/reportes/").data, [])  # los dos quedaron resueltos

    def test_descartar_un_reporte(self):
        resena = Resena.objects.create(usuario=self.sofia, concierto=self.pasado, general=4, texto=TEXTO, asistio=True)
        reporte = Reporte.objects.create(resena=resena, usuario=self.diego, motivo="falsa")
        self.client.post(f"/api/edicion/reportes/{reporte.pk}/descartar/")
        resena.refresh_from_db()
        reporte.refresh_from_db()
        self.assertEqual((resena.oculta, reporte.estado), (False, "descartado"))


class PerfilDeArtistaTests(EdicionTests):
    def setUp(self):
        super().setUp()
        self.como(self.editora)

    def test_alta_de_un_artista_sin_conciertos_con_su_perfil(self):
        respuesta = self.client.post("/api/edicion/artistas/", {
            "nombre": "Los Músicos de José", "genero": "Rock", "imagen_url": "https://img.mx/jose.jpg",
            "descripcion": "Banda de rock de Guanajuato.", "enlaces": {"instagram": "https://instagram.com/jose"},
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        artista = Artista.objects.get(nombre="Los Músicos de José")
        self.assertTrue(artista.descripcion_fija)  # la escribió una persona
        # Su perfil es público aunque no tenga conciertos, y sale en el buscador.
        self.client.force_authenticate(None)
        perfil = self.client.get(f"/api/artistas/{artista.slug}/").data
        self.assertEqual((perfil["descripcion"], perfil["proximos"]), ("Banda de rock de Guanajuato.", []))
        busqueda = self.client.get("/api/artistas/", {"q": "musicos de jose"}).data
        self.assertEqual([(a["nombre"], a["proximos"]) for a in busqueda], [("Los Músicos de José", 0)])

    def test_no_duplica_nombres_ni_acepta_enlaces_raros(self):
        self.assertEqual(self.client.post("/api/edicion/artistas/", {"nombre": "los cometas del sur"}, format="json").status_code, 200)
        url = f"/api/edicion/artistas/{self.cometas.slug}/"
        self.assertEqual(self.client.patch(url, {"nombre": "Marea Roja"}, format="json").status_code, 200)
        Artista.objects.create(nombre="Banda Uno")
        self.assertEqual(self.client.patch(url, {"nombre": "banda uno"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"enlaces": {"myspace": "https://x.mx"}}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"enlaces": {"instagram": "no es url"}}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"wikipedia": "https://www.google.com"}, format="json").status_code, 400)

    def test_editar_conserva_los_enlaces_internos_y_borrar_descripcion_la_libera(self):
        self.cometas.enlaces = {"musicbrainz": "https://musicbrainz.org/artist/x", "instagram": "https://ig.mx/viejo"}
        self.cometas.descripcion, self.cometas.descripcion_fija = "Escrita a mano.", True
        self.cometas.save()
        url = f"/api/edicion/artistas/{self.cometas.slug}/"
        self.client.patch(url, {"enlaces": {"spotify": "https://open.spotify.com/artist/x"}, "descripcion": ""}, format="json")
        self.cometas.refresh_from_db()
        self.assertEqual(self.cometas.enlaces, {"musicbrainz": "https://musicbrainz.org/artist/x", "spotify": "https://open.spotify.com/artist/x"})
        self.assertFalse(self.cometas.descripcion_fija)  # vacía: la búsqueda de la noche la llenará

    def test_pegar_un_articulo_busca_la_descripcion_al_momento(self):
        from unittest.mock import patch

        from conciertos.importacion.wikipedia import Resumen

        resumen = Resumen(titulo="Cometas", texto="Banda de Monterrey.", url="https://es.wikipedia.org/wiki/Cometas")
        with patch("conciertos.importacion.wikipedia.Wikipedia.buscar", return_value=resumen):
            self.client.patch(f"/api/edicion/artistas/{self.cometas.slug}/", {"wikipedia": "https://es.wikipedia.org/wiki/Cometas"}, format="json")
        self.cometas.refresh_from_db()
        self.assertEqual((self.cometas.descripcion, self.cometas.descripcion_fuente), ("Banda de Monterrey.", "https://es.wikipedia.org/wiki/Cometas"))

    def test_sin_rol_no_edita_perfiles(self):
        self.como(self.sofia)
        self.assertEqual(self.client.patch(f"/api/edicion/artistas/{self.cometas.slug}/", {"nombre": "X"}, format="json").status_code, 403)
