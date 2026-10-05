from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from conciertos.models import Artista, Ciudad, Concierto, PrecioZona, Recinto, inicio_de_hoy


class DatosDePrueba(APITestCase):
    """Cartelera pequeña: 3 próximos en CDMX, 1 en Guadalajara, 1 pasado y 1 cancelado."""

    def setUp(self):
        self.cdmx = Ciudad.objects.get(slug="cdmx")
        self.gdl = Ciudad.objects.get(slug="guadalajara")
        self.auditorio = Recinto.objects.create(nombre="Auditorio Nacional", ciudad=self.cdmx)
        self.foro = Recinto.objects.create(nombre="Foro Tezontle", ciudad=self.cdmx)
        self.minerva = Recinto.objects.create(nombre="Auditorio Minerva", ciudad=self.gdl)
        self.cometas = Artista.objects.create(nombre="Los Cometas del Sur", genero="Rock")
        self.niebla = Artista.objects.create(nombre="Niebla Eléctrica", genero="Electrónica")
        self.marea = Artista.objects.create(nombre="Marea Roja", genero="Latino")

        self.cometas_cdmx = self.crear(self.cometas, self.auditorio, dias=10, precio=780)
        self.niebla_cdmx = self.crear(self.niebla, self.foro, dias=3, precio=None)
        self.marea_cdmx = self.crear(self.marea, self.foro, dias=40, precio=450)
        self.cometas_gdl = self.crear(self.cometas, self.minerva, dias=20, precio=690)
        self.cometas_pasado = self.crear(self.cometas, self.auditorio, dias=-30, precio=700)
        self.cancelado = self.crear(self.cometas, self.foro, dias=15, precio=500, estado=Concierto.Estado.CANCELADO)
        self.cometas_cdmx.invitados.add(self.marea)

    def crear(self, artista, recinto, dias, precio, estado=Concierto.Estado.EN_VENTA):
        return Concierto.objects.create(
            titulo=artista.nombre, artista=artista, recinto=recinto,
            fecha_hora=timezone.now() + timedelta(days=dias),
            precio_desde=Decimal(precio) if precio is not None else None,
            estado=estado, url_boletos="https://boletera.example/x",
        )

    def lista(self, **parametros):
        respuesta = self.client.get(reverse("conciertos"), parametros)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def slugs(self, **parametros):
        return [c["slug"] for c in self.lista(**parametros)["resultados"]]


class CiudadesTests(DatosDePrueba):
    def test_cuenta_solo_conciertos_proximos_no_cancelados(self):
        datos = {c["slug"]: c for c in self.client.get(reverse("ciudades")).json()}
        self.assertEqual(datos["cdmx"]["conciertos_proximos"], 3)
        self.assertEqual(datos["guadalajara"]["conciertos_proximos"], 1)
        self.assertEqual(datos["puebla"]["conciertos_proximos"], 0)
        self.assertTrue(datos["cdmx"]["es_predeterminada"])


class ListaConciertosTests(DatosDePrueba):
    def test_excluye_pasados_y_cancelados_y_ordena_por_fecha(self):
        self.assertEqual(
            self.slugs(),
            [self.niebla_cdmx.slug, self.cometas_cdmx.slug, self.cometas_gdl.slug, self.marea_cdmx.slug],
        )

    def test_concierto_de_hoy_sigue_en_cartelera(self):
        # Hora por confirmar: se guarda a medianoche, que ya pasó, pero el concierto es hoy.
        hoy = self.crear(self.marea, self.minerva, dias=0, precio=None)
        hoy.fecha_hora = inicio_de_hoy()
        hoy.save()
        self.assertIn(hoy.slug, self.slugs(ciudad="guadalajara"))

    def test_filtra_por_ciudad(self):
        self.assertEqual(self.slugs(ciudad="guadalajara"), [self.cometas_gdl.slug])
        self.assertEqual(self.slugs(ciudad="puebla"), [])

    def test_busca_sin_acentos_ni_mayusculas(self):
        self.assertEqual(self.slugs(q="ELECTRICA"), [self.niebla_cdmx.slug])

    def test_busca_por_recinto_y_genero(self):
        self.assertEqual(self.slugs(q="tezontle"), [self.niebla_cdmx.slug, self.marea_cdmx.slug])
        self.assertEqual(self.slugs(q="rock", ciudad="cdmx"), [self.cometas_cdmx.slug])

    def test_busca_por_invitado_sin_repetir(self):
        otro = Artista.objects.create(nombre="Marea Baja")
        self.cometas_cdmx.invitados.add(otro)  # dos invitados coinciden con "marea"
        self.assertEqual(self.slugs(q="marea", ciudad="cdmx"), [self.cometas_cdmx.slug, self.marea_cdmx.slug])

    def test_filtra_por_rango_de_fechas(self):
        desde = (timezone.localdate() + timedelta(days=5)).isoformat()
        hasta = (timezone.localdate() + timedelta(days=25)).isoformat()
        self.assertEqual(self.slugs(desde=desde, hasta=hasta), [self.cometas_cdmx.slug, self.cometas_gdl.slug])

    def test_fecha_invalida_responde_400(self):
        respuesta = self.client.get(reverse("conciertos"), {"desde": "mañana"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("desde", respuesta.json())

    def test_orden_por_precio_deja_al_final_los_que_no_tienen(self):
        self.assertEqual(
            self.slugs(orden="precio", ciudad="cdmx"),
            [self.marea_cdmx.slug, self.cometas_cdmx.slug, self.niebla_cdmx.slug],
        )

    def test_datos_del_boleto(self):
        concierto = self.lista(ciudad="guadalajara")["resultados"][0]
        self.assertEqual(concierto["artista"]["nombre"], "Los Cometas del Sur")
        self.assertEqual(concierto["recinto"]["ciudad"], {"nombre": "Guadalajara", "slug": "guadalajara"})
        self.assertEqual(concierto["precio_desde"], 690)  # número, no texto

    def test_paginacion(self):
        for dias in range(50, 75):
            self.crear(self.marea, self.minerva, dias=dias, precio=300)
        primera = self.lista(ciudad="guadalajara")
        self.assertEqual(primera["total"], 26)
        self.assertEqual(len(primera["resultados"]), 20)
        self.assertIsNotNone(primera["siguiente"])
        segunda = self.lista(ciudad="guadalajara", pagina=2)
        self.assertEqual(len(segunda["resultados"]), 6)
        self.assertIsNone(segunda["siguiente"])

    def test_no_hace_una_consulta_por_concierto(self):
        # 1 para contar (paginación) + 1 para la lista con artista, recinto y ciudad.
        with self.assertNumQueries(2):
            self.lista()


class DetalleConciertoTests(DatosDePrueba):
    def detalle(self, concierto):
        respuesta = self.client.get(reverse("concierto-detalle", args=[concierto.slug]))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()

    def test_datos_completos(self):
        PrecioZona.objects.create(concierto=self.cometas_cdmx, zona="Gradas", precio=780)
        PrecioZona.objects.create(concierto=self.cometas_cdmx, zona="Pista", precio=1720)
        datos = self.detalle(self.cometas_cdmx)
        self.assertEqual(datos["recinto"]["nombre"], "Auditorio Nacional")
        self.assertEqual([i["nombre"] for i in datos["invitados"]], ["Marea Roja"])
        self.assertEqual(datos["precios"], [{"zona": "Pista", "precio": 1720}, {"zona": "Gradas", "precio": 780}])
        self.assertEqual(datos["url_boletos"], "https://boletera.example/x")
        self.assertFalse(datos["ya_paso"])

    def test_otras_fechas_del_artista(self):
        otras = self.detalle(self.cometas_cdmx)["otras_fechas"]
        # Incluye la pasada (para las reseñas) y la de Guadalajara; no la cancelada ni la propia.
        self.assertEqual([o["slug"] for o in otras], [self.cometas_pasado.slug, self.cometas_gdl.slug])
        self.assertEqual([o["ya_paso"] for o in otras], [True, False])

    def test_abre_conciertos_pasados_y_cancelados(self):
        self.assertTrue(self.detalle(self.cometas_pasado)["ya_paso"])
        self.assertEqual(self.detalle(self.cancelado)["estado"], "cancelado")

    def test_slug_inexistente_responde_404(self):
        respuesta = self.client.get(reverse("concierto-detalle", args=["no-existe"]))
        self.assertEqual(respuesta.status_code, 404)


class SaludTests(APITestCase):
    def test_responde_sin_consultar_la_base(self):
        with self.assertNumQueries(0):
            respuesta = self.client.get(reverse("salud"))
        self.assertEqual(respuesta.json(), {"ok": True})
