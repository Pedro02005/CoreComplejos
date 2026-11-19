from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from complejos.models import Cancha, Complejo
from reservas.models import Reserva


class ApiClientesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="cliente_api", email="existente@example.com", password="ClaveSegura123!",
        )
        cls.otro = get_user_model().objects.create_user(username="otro_api", email="otro_api@example.com")
        complejo = Complejo.objects.create(nombre="Centro API", ciudad="Quito", direccion="Norte")
        cancha = Cancha.objects.create(complejo=complejo, nombre="Cancha API", deporte="TENIS", capacidad=4)
        ahora = timezone.now()
        # Historial de otro cliente: no debe aparecer en las estadísticas personales.
        Reserva.objects.create(
            cliente=cls.otro, cancha=cancha, inicio=ahora - timedelta(days=2),
            fin=ahora - timedelta(days=2, hours=-1), total=Decimal("20.00"),
            clave_solicitud=uuid4(), cancelable_hasta=ahora - timedelta(days=3),
        )

    def datos_registro(self, **cambios):
        return {
            "username": "nueva_cuenta", "first_name": "Ana", "last_name": "Perez",
            "email": "ana@example.com", "password": "MiReservaFuerte123!",
            "password_confirmacion": "MiReservaFuerte123!", **cambios,
        }

    def test_registro_publico_crea_cliente_y_cifra_password(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos_registro(
            rol="ADMIN_PLATAFORMA", is_staff=True, is_superuser=True, complejo=999,
        ))
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        usuario = get_user_model().objects.get(username="nueva_cuenta")
        self.assertEqual(usuario.rol, "CLIENTE")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertIsNone(usuario.complejo_id)
        self.assertTrue(usuario.check_password("MiReservaFuerte123!"))
        self.assertNotIn("password", respuesta.data)

    def test_registro_valida_confirmacion_y_seguridad_de_password(self):
        for cambios in (
            {"password_confirmacion": "OtraClave"},
            {"password": "123", "password_confirmacion": "123"},
        ):
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(reverse("cuentas:registro"), self.datos_registro(**cambios))
                self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username="nueva_cuenta").exists())

    def test_registro_rechaza_correo_duplicado_sin_distinguir_mayusculas(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos_registro(email="EXISTENTE@example.com"))
        self.assertEqual(respuesta.status_code, 400)

    def test_registro_valida_usuario_cedula_y_telefono(self):
        for cambios in (
            {"username": self.usuario.username}, {"cedula": "123"},
            {"telefono": "123"}, {"email": "no-es-correo"}, {"first_name": ""},
        ):
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(reverse("cuentas:registro"), self.datos_registro(**cambios))
                self.assertEqual(respuesta.status_code, 400)

    def test_registro_normaliza_correo_y_documento_vacio(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos_registro(email="ANA@EXAMPLE.COM", cedula="", telefono=""))
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(respuesta.data["email"], "ana@example.com")
        self.assertIsNone(respuesta.data["cedula"])

    def test_perfil_y_estadisticas_requieren_autenticacion(self):
        for nombre in ("cuentas:perfil", "mis-estadisticas"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 401)

    def test_perfil_solo_actualiza_datos_personales(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.patch(reverse("cuentas:perfil"), {
            "first_name": "Actualizado", "telefono": "0991234567", "rol": "ADMIN_PLATAFORMA",
            "is_superuser": True, "username": "otro_nombre", "complejo": 999,
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "Actualizado")
        self.assertEqual(self.usuario.username, "cliente_api")
        self.assertEqual(self.usuario.rol, "CLIENTE")
        self.assertFalse(self.usuario.is_superuser)
        self.assertIsNone(self.usuario.complejo_id)
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.first_name, "")

    def test_perfil_no_acepta_correo_duplicado_o_telefono_invalido(self):
        self.client.force_authenticate(self.usuario)
        for datos in ({"email": "OTRO_API@example.com"}, {"telefono": "000"}):
            with self.subTest(datos=datos):
                self.assertEqual(self.client.patch(reverse("cuentas:perfil"), datos).status_code, 400)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "existente@example.com")

    def test_estadisticas_no_mezclan_clientes_y_validan_periodo(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get(reverse("mis-estadisticas"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["historial"]["periodo_dias"], 90)
        self.assertEqual(respuesta.data["historial"]["reservas_finalizadas"], 0)
        self.assertIsNone(respuesta.data["encuestas"]["experiencias"]["calificacion_promedio"])
        for dias in (0, 366, "abc"):
            self.assertEqual(self.client.get(reverse("mis-estadisticas"), {"dias": dias}).status_code, 400)
        self.client.force_authenticate(self.otro)
        respuesta = self.client.get(reverse("mis-estadisticas"), {"dias": 30})
        self.assertEqual(respuesta.data["historial"]["reservas_finalizadas"], 1)

    def test_login_jwt_permite_consultar_perfil(self):
        respuesta = self.client.post(reverse("token_obtain_pair"), {"username": "cliente_api", "password": "ClaveSegura123!"})
        self.assertEqual(respuesta.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
        perfil = self.client.get(reverse("cuentas:perfil"))
        self.assertEqual(perfil.status_code, 200)
        self.assertEqual(perfil.data["id"], self.usuario.pk)
        self.assertFalse(perfil.data["es_administrador"])

    def test_perfil_identifica_superusuario_aunque_tenga_rol_cliente(self):
        tecnico = get_user_model().objects.create_superuser(
            username="tecnico_api", email="tecnico_api@example.com", password="ClaveSegura123!",
        )
        self.client.force_authenticate(tecnico)
        respuesta = self.client.get(reverse("cuentas:perfil"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["es_administrador"])

    def test_cors_permite_frontend_local_y_rechaza_otro_origen(self):
        respuesta = self.client.options(reverse("token_obtain_pair"),
            HTTP_ORIGIN="http://localhost:5173", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(respuesta["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("authorization", respuesta["Access-Control-Allow-Headers"])
        respuesta = self.client.options(reverse("token_obtain_pair"),
            HTTP_ORIGIN="https://otro-origen.example", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", respuesta)
