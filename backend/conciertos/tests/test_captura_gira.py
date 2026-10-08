"""Captura de una gira con varias fechas desde el panel."""
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from conciertos.models import Artista, Ciudad, Concierto, Recinto

URL = reverse("admin:conciertos_capturar_gira")
MEXICO = ZoneInfo("America/Mexico_City")


class CapturarGiraTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", "admin@correo.mx", "clave-admin-larga")
        self.client.force_login(self.admin)
        self.artista = Artista.objects.create(nombre="Café Tacvba", genero="Rock")
        self.auditorio = Recinto.objects.create(nombre="Auditorio Nacional", ciudad=Ciudad.objects.get(slug="cdmx"))
        self.diana = Recinto.objects.create(nombre="Teatro Diana", ciudad=Ciudad.objects.get(slug="guadalajara"))

    def enviar(self, filas, **comunes):
        datos = {
            "artista": self.artista.pk, "gira": "Gira Re 2026", "url_boletos": "https://boletos.mx/tacvba",
            "imagen_url": "", "genero": "", **comunes,
            "fechas-TOTAL_FORMS": "6", "fechas-INITIAL_FORMS": "0", "fechas-MIN_NUM_FORMS": "1", "fechas-MAX_NUM_FORMS": "1000",
        }
        for i, fila in enumerate(filas):
            datos.update({f"fechas-{i}-{campo}": valor for campo, valor in fila.items()})
        return self.client.post(URL, datos)

    def test_la_pantalla_carga_y_la_lista_tiene_el_boton(self):
        self.assertEqual(self.client.get(URL).status_code, 200)
        lista = self.client.get(reverse("admin:conciertos_concierto_changelist"))
        self.assertContains(lista, "Capturar gira")

    def test_crea_un_concierto_por_fila_e_ignora_las_vacias(self):
        respuesta = self.enviar([
            {"recinto": self.auditorio.pk, "fecha": "2026-12-12", "hora": "21:00"},
            {"recinto": self.diana.pk, "fecha": "2026-12-14", "url_boletos": "https://otra.mx", "precio_desde": "650"},
        ])
        self.assertEqual(respuesta.status_code, 302)
        cdmx, gdl = Concierto.objects.order_by("fecha_hora")
        self.assertEqual(cdmx.fecha_hora, datetime(2026, 12, 12, 21, tzinfo=MEXICO))
        self.assertEqual((cdmx.gira, cdmx.genero, cdmx.origen), ("Gira Re 2026", "Rock", Concierto.Origen.MANUAL))
        self.assertEqual(cdmx.url_boletos, "https://boletos.mx/tacvba")
        self.assertTrue(gdl.hora_por_confirmar)  # sin hora
        self.assertEqual((gdl.url_boletos, gdl.precio_desde), ("https://otra.mx", 650))
        self.assertEqual(gdl.slug, "cafe-tacvba-guadalajara-2026-12-14")

    def test_si_una_fecha_ya_existe_no_guarda_ninguna(self):
        Concierto.objects.create(
            titulo="Café Tacvba", artista=self.artista, recinto=self.auditorio,
            fecha_hora=datetime(2026, 12, 12, 20, tzinfo=MEXICO), url_boletos="https://boletos.mx",
        )
        respuesta = self.enviar([
            {"recinto": self.diana.pk, "fecha": "2026-12-14"},
            {"recinto": self.auditorio.pk, "fecha": "2026-12-12", "hora": "21:00"},
        ])
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ya existe")
        self.assertEqual(Concierto.objects.count(), 1)

    def test_misma_ciudad_y_dia_repetidos_en_la_tabla(self):
        respuesta = self.enviar([
            {"recinto": self.auditorio.pk, "fecha": "2026-12-12"},
            {"recinto": self.auditorio.pk, "fecha": "2026-12-12"},
        ])
        self.assertContains(respuesta, "ya están en otra fila")
        self.assertFalse(Concierto.objects.exists())

    def test_al_menos_una_fecha(self):
        respuesta = self.enviar([])
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Concierto.objects.exists())

    def test_solo_con_permiso(self):
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 302)  # al login del panel
        sin_permiso = get_user_model().objects.create_user("staff", "staff@correo.mx", "clave-staff-larga", is_staff=True)
        self.client.force_login(sin_permiso)
        self.assertEqual(self.client.get(URL).status_code, 403)
