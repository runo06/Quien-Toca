from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

Usuario = get_user_model()
CLAVE = "conciertos-en-vivo-2026"


class CuentasTests(APITestCase):
    def setUp(self):
        cache.clear()  # el freno por IP vive en la caché: cada prueba empieza de cero

    def registrar(self, **datos):
        datos = {"nombre": "Sofía M.", "email": "Sofia@Correo.mx", "password": CLAVE, **datos}
        return self.client.post(reverse("registro"), datos)

    def entrar(self, email="sofia@correo.mx", password=CLAVE):
        return self.client.post(reverse("entrar"), {"email": email, "password": password})

    def test_registro_crea_la_cuenta_y_entrega_tokens(self):
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["usuario"]["nombre"], "Sofía M.")
        self.assertEqual(respuesta.data["usuario"]["email"], "sofia@correo.mx")  # en minúsculas
        self.assertIn("access", respuesta.data)
        self.assertIn("refresh", respuesta.data)
        self.assertTrue(Usuario.objects.get(username="sofia@correo.mx").check_password(CLAVE))

    def test_no_repite_correo_aunque_cambien_mayusculas(self):
        self.registrar()
        respuesta = self.registrar(email="SOFIA@correo.mx")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("email", respuesta.data)

    def test_rechaza_contrasenas_debiles(self):
        for clave in ["123", "12345678901", "password123"]:
            with self.subTest(clave=clave):
                respuesta = self.registrar(password=clave)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("password", respuesta.data)

    def test_entrar_con_correo_y_contrasena(self):
        self.registrar()
        respuesta = self.entrar(email="SOFIA@correo.mx")
        self.assertEqual(respuesta.status_code, 200)
        yo = self.client.get(reverse("yo"), HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
        self.assertEqual(yo.data["nombre"], "Sofía M.")

    def test_contrasena_incorrecta_no_dice_si_el_correo_existe(self):
        self.registrar()
        mala_clave = self.entrar(password="otra-cosa-distinta")
        sin_cuenta = self.entrar(email="nadie@correo.mx")
        self.assertEqual(mala_clave.status_code, 401)
        self.assertEqual(mala_clave.data, sin_cuenta.data)

    def test_yo_sin_sesion_responde_401(self):
        self.assertEqual(self.client.get(reverse("yo")).status_code, 401)

    def test_renovar_cambia_el_refresh_y_anula_el_viejo(self):
        refresh = self.registrar().data["refresh"]
        renovado = self.client.post(reverse("renovar"), {"refresh": refresh})
        self.assertEqual(renovado.status_code, 200)
        self.assertNotEqual(renovado.data["refresh"], refresh)
        self.assertEqual(self.client.post(reverse("renovar"), {"refresh": refresh}).status_code, 401)

    def test_salir_anula_el_refresh(self):
        refresh = self.registrar().data["refresh"]
        self.assertEqual(self.client.post(reverse("salir"), {"refresh": refresh}).status_code, 205)
        self.assertEqual(self.client.post(reverse("renovar"), {"refresh": refresh}).status_code, 401)

    def test_frena_muchos_intentos_seguidos(self):
        respuestas = [self.entrar(password=f"intento-{n}").status_code for n in range(11)]
        self.assertEqual(respuestas[:10], [401] * 10)
        self.assertEqual(respuestas[10], 429)
