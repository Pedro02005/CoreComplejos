from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from complejos.models import Bloqueo, Cancha, Complejo, HorarioAtencion, Tarifa
from reservas.models import Encuesta, HistorialReserva
from reservas.services.cancelacion import cancelar_reserva
from reservas.services.reserva import confirmar_reserva
from .models import Usuario


class PermisosRolesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.complejo = Complejo.objects.create(nombre="Centro propio", ciudad="Quito", direccion="Norte")
        cls.ajeno = Complejo.objects.create(nombre="Centro ajeno", ciudad="Cuenca", direccion="Sur")
        cls.cliente = Usuario.objects.create_user(username="cliente", email="cliente@example.com", password="ClaveSegura123!")
        cls.otro_cliente = Usuario.objects.create_user(username="otro", email="otro@example.com")
        cls.administrador = Usuario.objects.create_user(
            username="gestor", email="gestor@example.com", password="ClaveSegura123!",
            rol="ADMIN_COMPLEJO", complejo=cls.complejo,
        )
        cls.coadministrador = Usuario.objects.create_user(
            username="cogestor", email="cogestor@example.com", rol="ADMIN_COMPLEJO", complejo=cls.complejo,
        )
        cls.admin_ajeno = Usuario.objects.create_user(
            username="gestor_ajeno", email="gestor_ajeno@example.com", rol="ADMIN_COMPLEJO", complejo=cls.ajeno,
        )
        cls.plataforma = Usuario.objects.create_user(
            username="plataforma", email="plataforma@example.com", rol="ADMIN_PLATAFORMA",
        )
        cls.superusuario = Usuario.objects.create_superuser(
            username="tecnico", email="tecnico@example.com", password="ClaveSegura123!",
        )
        fecha = timezone.localdate() + timedelta(days=3)
        cls.inicio = datetime.combine(fecha, time(17), tzinfo=ZoneInfo("America/Guayaquil"))
        cls.fin = cls.inicio + timedelta(hours=1)
        cls.canchas = []
        cls.tarifas = []
        cls.horarios = []
        cls.reservas = []
        for complejo in (cls.complejo, cls.ajeno):
            cancha = Cancha.objects.create(
                complejo=complejo, nombre=f"Cancha {complejo.nombre}", deporte="FUTBOL", capacidad=10,
            )
            cls.canchas.append(cancha)
            cls.horarios.append(HorarioAtencion.objects.create(
                cancha=cancha, dia_semana=fecha.weekday(), apertura=time(8), cierre=time(22),
            ))
            cls.tarifas.append(Tarifa.objects.create(
                cancha=cancha, dia_semana=fecha.weekday(), inicio=time(8), fin=time(22), valor_hora=Decimal("20.00"),
            ))
            cls.reservas.append(confirmar_reserva(cls.cliente, cancha, cls.inicio, cls.fin))
        cls.bloqueos = [
            Bloqueo.objects.create(
                cancha=cancha, administrador=cls.superusuario,
                inicio=cls.inicio + timedelta(days=1), fin=cls.fin + timedelta(days=1), motivo="Mantenimiento",
            ) for cancha in cls.canchas
        ]

    def login_admin(self, usuario=None):
        self.client.force_login(usuario or self.administrador)

    def test_un_complejo_admite_varios_administradores(self):
        self.assertEqual(
            set(self.complejo.administradores.values_list("pk", flat=True)),
            {self.administrador.pk, self.coadministrador.pk},
        )
        self.assertEqual(self.administrador.complejo_id, self.complejo.pk)

    def test_asignacion_se_valida_segun_rol(self):
        casos = (("ADMIN_COMPLEJO", None), ("CLIENTE", self.complejo), ("ADMIN_PLATAFORMA", self.complejo))
        for rol, complejo in casos:
            with self.subTest(rol=rol):
                usuario = Usuario(username="nuevo", email="nuevo@example.com", rol=rol, complejo=complejo)
                with self.assertRaises(ValidationError) as error:
                    usuario.full_clean()
                self.assertIn("complejo", error.exception.message_dict)

    def test_base_de_datos_rechaza_asignaciones_invalidas(self):
        for rol, complejo in (("ADMIN_COMPLEJO", None), ("CLIENTE", self.complejo)):
            with self.subTest(rol=rol):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Usuario.objects.create(username="invalido", email="invalido@example.com", rol=rol, complejo=complejo)

    def test_acceso_staff_acompana_al_rol_sin_conceder_superusuario(self):
        self.assertFalse(self.cliente.is_staff)
        self.assertTrue(self.administrador.is_staff)
        self.assertTrue(self.plataforma.is_staff)
        self.assertFalse(self.administrador.is_superuser)
        self.administrador.rol = "CLIENTE"
        self.administrador.complejo = None
        self.administrador.save(update_fields=["rol", "complejo"])
        self.administrador.refresh_from_db()
        self.assertFalse(self.administrador.is_staff)
        self.assertFalse(self.administrador.has_perm("complejos.change_cancha"))

    def test_login_real_del_administrador_y_token_jwt(self):
        self.assertTrue(self.client.login(username="gestor", password="ClaveSegura123!"))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        respuesta = self.client.post(reverse("token_obtain_pair"), {"username": "gestor", "password": "ClaveSegura123!"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.data)

    def test_cliente_no_tiene_acceso_al_admin_ni_con_permisos_manuales(self):
        permiso = Permission.objects.get(content_type__app_label="cuentas", codename="change_usuario")
        self.cliente.user_permissions.add(permiso)
        Usuario.objects.filter(pk=self.cliente.pk).update(is_staff=True)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.has_perm("cuentas.change_usuario"))
        self.login_admin(self.cliente)
        self.assertEqual(self.client.get(reverse("admin:cuentas_usuario_changelist")).status_code, 302)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.is_staff)

    def test_administrador_inactivo_o_sin_staff_no_tiene_permisos(self):
        self.administrador.is_active = False
        self.assertFalse(self.administrador.has_perm("complejos.change_cancha"))
        self.administrador.is_active = True
        self.administrador.is_staff = False
        self.assertFalse(self.administrador.has_perm("complejos.change_cancha"))

    def test_listados_admin_se_limitan_al_complejo(self):
        self.login_admin()
        casos = (
            ("complejos_complejo", self.complejo.pk),
            ("complejos_cancha", self.canchas[0].pk),
            ("complejos_horarioatencion", self.horarios[0].pk),
            ("complejos_tarifa", self.tarifas[0].pk),
            ("complejos_bloqueo", self.bloqueos[0].pk),
            ("reservas_reserva", self.reservas[0].pk),
        )
        for modelo, esperado in casos:
            with self.subTest(modelo=modelo):
                respuesta = self.client.get(reverse(f"admin:{modelo}_changelist"))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(list(respuesta.context["cl"].queryset.values_list("pk", flat=True)), [esperado])
                self.assertNotContains(respuesta, self.ajeno.nombre)

    def test_acceso_directo_y_post_a_registros_ajenos_no_modifica(self):
        self.login_admin()
        for modelo, objeto in (
            ("complejos_complejo", self.ajeno), ("complejos_cancha", self.canchas[1]),
            ("complejos_horarioatencion", self.horarios[1]), ("complejos_tarifa", self.tarifas[1]),
            ("complejos_bloqueo", self.bloqueos[1]), ("reservas_reserva", self.reservas[1]),
        ):
            with self.subTest(modelo=modelo):
                url = reverse(f"admin:{modelo}_change", args=[objeto.pk])
                respuesta = self.client.get(url)
                self.assertIn(respuesta.status_code, (302, 403, 404))
                self.assertIn(self.client.post(url, {"nombre": "Intrusion"}).status_code, (302, 403, 404))
        self.ajeno.refresh_from_db()
        self.assertEqual(self.ajeno.nombre, "Centro ajeno")

    def test_administrador_puede_crear_cancha_propia_pero_no_ajena(self):
        self.login_admin()
        datos = {"complejo": self.complejo.pk, "nombre": "Nueva cancha", "deporte": "TENIS", "capacidad": 4, "activa": "on"}
        url = reverse("admin:complejos_cancha_add")
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.assertTrue(Cancha.objects.filter(nombre="Nueva cancha", complejo=self.complejo).exists())
        datos.update(complejo=self.ajeno.pk, nombre="Cancha intrusa")
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("complejo", respuesta.context["adminform"].form.errors)
        self.assertFalse(Cancha.objects.filter(nombre="Cancha intrusa").exists())

    def test_administrador_no_puede_mover_su_cancha_a_otro_complejo(self):
        self.login_admin()
        respuesta = self.client.post(
            reverse("admin:complejos_cancha_change", args=[self.canchas[0].pk]),
            {"complejo": self.ajeno.pk, "nombre": self.canchas[0].nombre, "deporte": "FUTBOL", "capacidad": 10, "activa": "on"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.canchas[0].refresh_from_db()
        self.assertEqual(self.canchas[0].complejo_id, self.complejo.pk)

    def test_selectores_y_autocompletado_solo_ofrecen_registros_propios(self):
        self.login_admin()
        for campo, modelo, esperado in (
            ("complejo", "cancha", self.complejo.pk),
            ("cancha", "horarioatencion", self.canchas[0].pk),
        ):
            with self.subTest(campo=campo):
                respuesta = self.client.get(reverse("admin:autocomplete"), {
                    "app_label": "complejos", "model_name": modelo, "field_name": campo, "term": "",
                })
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual([item["id"] for item in respuesta.json()["results"]], [str(esperado)])

    def test_formulario_tarifa_y_selector_dependiente_respetan_complejo(self):
        self.login_admin()
        respuesta = self.client.get(reverse("admin:complejos_tarifa_change", args=[self.tarifas[0].pk]))
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context["adminform"].form
        self.assertEqual(list(formulario.fields["complejo"].queryset), [self.complejo])
        self.assertEqual(list(formulario.fields["cancha"].queryset), [self.canchas[0]])
        url = reverse("admin:complejos_tarifa_canchas")
        self.assertEqual(self.client.get(url, {"complejo_id": self.ajeno.pk}).json()["canchas"], [])
        propias = self.client.get(url, {"complejo_id": self.complejo.pk}).json()["canchas"]
        self.assertEqual([cancha["id"] for cancha in propias], [self.canchas[0].pk])
        datos = {"complejo": self.ajeno.pk, "cancha": self.canchas[1].pk, "dia_semana": 0, "inicio": "08:00", "fin": "09:00", "valor_hora": "5.00", "activa": "on"}
        respuesta = self.client.post(reverse("admin:complejos_tarifa_add"), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("complejo", respuesta.context["adminform"].form.errors)
        self.assertIn("cancha", respuesta.context["adminform"].form.errors)
        self.assertFalse(Tarifa.objects.filter(valor_hora="5.00").exists())

    def test_bloqueo_registra_al_administrador_autenticado(self):
        self.login_admin()
        inicio = timezone.localtime(self.inicio + timedelta(days=2))
        fin = inicio + timedelta(hours=1)
        respuesta = self.client.post(reverse("admin:complejos_bloqueo_add"), {
            "cancha": self.canchas[0].pk, "administrador": self.superusuario.pk,
            "inicio_0": inicio.strftime("%Y-%m-%d"), "inicio_1": inicio.strftime("%H:%M:%S"),
            "fin_0": fin.strftime("%Y-%m-%d"), "fin_1": fin.strftime("%H:%M:%S"),
            "motivo": "Reparacion", "activo": "on",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Bloqueo.objects.get(motivo="Reparacion").administrador_id, self.administrador.pk)

    def test_administrador_no_gestiona_usuarios_complejos_nuevos_o_campanas(self):
        self.login_admin()
        for nombre in ("cuentas_usuario_changelist", "cuentas_usuario_add", "complejos_complejo_add", "reservas_promocion_changelist", "auth_group_changelist"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(f"admin:{nombre}")).status_code, 403)
        self.assertFalse(self.administrador.has_perm("complejos.delete_cancha"))

    def test_dos_administradores_del_mismo_complejo_comparten_acceso(self):
        self.login_admin(self.coadministrador)
        respuesta = self.client.get(reverse("admin:complejos_cancha_change", args=[self.canchas[0].pk]))
        self.assertEqual(respuesta.status_code, 200)

    def test_cambio_de_asignacion_revoca_acceso_al_complejo_anterior(self):
        self.login_admin()
        self.administrador.complejo = self.ajeno
        self.administrador.save(update_fields=["complejo"])
        respuesta = self.client.get(reverse("admin:complejos_cancha_changelist"))
        self.assertEqual(list(respuesta.context["cl"].queryset), [self.canchas[1]])

    def test_plataforma_y_superusuario_pueden_consultar_ambos_complejos(self):
        for usuario in (self.plataforma, self.superusuario):
            with self.subTest(usuario=usuario.username):
                self.login_admin(usuario)
                respuesta = self.client.get(reverse("admin:complejos_cancha_changelist"))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context["cl"].queryset.count(), 2)

    def test_plataforma_crea_administrador_y_asigna_complejo_sin_escalar_privilegios(self):
        self.login_admin(self.plataforma)
        respuesta = self.client.post(reverse("admin:cuentas_usuario_add"), {
            "username": "nuevo_admin", "email": "nuevo_admin@example.com", "rol": "ADMIN_COMPLEJO",
            "complejo": self.complejo.pk, "password1": "ClaveSegura123!", "password2": "ClaveSegura123!",
            "is_superuser": "on", "is_staff": "on",
        })
        self.assertEqual(respuesta.status_code, 302)
        nuevo = Usuario.objects.get(username="nuevo_admin")
        self.assertTrue(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        self.assertEqual(nuevo.complejo_id, self.complejo.pk)

    def test_plataforma_no_puede_crear_otro_admin_plataforma(self):
        self.login_admin(self.plataforma)
        respuesta = self.client.post(reverse("admin:cuentas_usuario_add"), {
            "username": "intruso", "email": "intruso@example.com", "rol": "ADMIN_PLATAFORMA",
            "password1": "ClaveSegura123!", "password2": "ClaveSegura123!",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("rol", respuesta.context["adminform"].form.errors)
        self.assertFalse(Usuario.objects.filter(username="intruso").exists())

    def test_plataforma_puede_asignar_cliente_sin_conceder_privilegios_tecnicos(self):
        self.login_admin(self.plataforma)
        permiso = Permission.objects.get(content_type__app_label="cuentas", codename="change_usuario")
        respuesta = self.client.post(reverse("admin:cuentas_usuario_change", args=[self.otro_cliente.pk]), {
            "username": self.otro_cliente.username, "email": self.otro_cliente.email,
            "rol": "ADMIN_COMPLEJO", "complejo": self.complejo.pk, "is_active": "on",
            "is_superuser": "on", "groups": [1], "user_permissions": [permiso.pk],
        })
        self.assertEqual(respuesta.status_code, 302)
        self.otro_cliente.refresh_from_db()
        self.assertTrue(self.otro_cliente.is_staff)
        self.assertFalse(self.otro_cliente.is_superuser)
        self.assertEqual(self.otro_cliente.complejo_id, self.complejo.pk)
        self.assertFalse(self.otro_cliente.user_permissions.exists())
        self.assertFalse(self.otro_cliente.groups.exists())

    def test_plataforma_no_modifica_cuentas_tecnicas_ni_su_propio_rol(self):
        self.login_admin(self.plataforma)
        respuesta = self.client.get(reverse("admin:cuentas_usuario_changelist"))
        ids = set(respuesta.context["cl"].queryset.values_list("pk", flat=True))
        self.assertNotIn(self.superusuario.pk, ids)
        self.assertNotIn(self.plataforma.pk, ids)
        for usuario in (self.superusuario, self.plataforma):
            respuesta = self.client.get(reverse("admin:cuentas_usuario_change", args=[usuario.pk]))
            self.assertIn(respuesta.status_code, (302, 403, 404))

    def test_formulario_edicion_plataforma_no_expone_privilegios_tecnicos(self):
        self.login_admin(self.plataforma)
        respuesta = self.client.get(reverse("admin:cuentas_usuario_change", args=[self.administrador.pk]))
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context["adminform"].form
        for campo in ("is_staff", "is_superuser", "groups", "user_permissions"):
            self.assertNotIn(campo, formulario.fields)

    def test_reservas_api_se_filtran_por_rol_y_asignacion(self):
        casos = (
            (self.cliente, {reserva.pk for reserva in self.reservas}),
            (self.otro_cliente, set()), (self.administrador, {self.reservas[0].pk}),
            (self.admin_ajeno, {self.reservas[1].pk}),
            (self.plataforma, {reserva.pk for reserva in self.reservas}),
        )
        for usuario, esperados in casos:
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(user=usuario)
                respuesta = self.client.get(reverse("confirmar-reserva"))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual({item["id"] for item in respuesta.data}, esperados)

    def test_api_impide_detalle_y_cancelacion_de_otro_complejo(self):
        self.client.force_authenticate(user=self.administrador)
        self.assertEqual(self.client.get(reverse("detalle-reserva", args=[self.reservas[0].pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("detalle-reserva", args=[self.reservas[1].pk])).status_code, 404)
        respuesta = self.client.post(reverse("cancelar-reserva", args=[self.reservas[1].pk]), {"motivo": "No autorizado"})
        self.assertEqual(respuesta.status_code, 404)
        self.reservas[1].refresh_from_db()
        self.assertEqual(self.reservas[1].estado, "CONFIRMADA")

    def test_servicio_cancelacion_exige_complejo_y_motivo(self):
        with self.assertRaises(PermissionDenied):
            cancelar_reserva(self.reservas[1], self.administrador, "Otro complejo")
        with self.assertRaises(ValidationError):
            cancelar_reserva(self.reservas[0], self.administrador)
        cancelar_reserva(self.reservas[0], self.administrador, "Mantenimiento urgente")
        self.assertTrue(HistorialReserva.objects.filter(
            reserva=self.reservas[0], actor=self.administrador, evento="CANCELACION", motivo="Mantenimiento urgente",
        ).exists())

    def test_cancelacion_desde_admin_solo_afecta_reservas_del_complejo(self):
        self.login_admin()
        respuesta = self.client.post(reverse("admin:reservas_reserva_changelist"), {
            "action": "cancelar_reservas", "_selected_action": [reserva.pk for reserva in self.reservas],
            "motivo": "Mantenimiento urgente", "index": "0",
        })
        self.assertEqual(respuesta.status_code, 302)
        for reserva in self.reservas:
            reserva.refresh_from_db()
        self.assertEqual(self.reservas[0].estado, "CANCELADA")
        self.assertEqual(self.reservas[1].estado, "CONFIRMADA")
        self.assertTrue(Encuesta.objects.filter(reserva=self.reservas[0], tipo="CANCELACION").exists())

    def test_cancelacion_desde_admin_sin_motivo_no_modifica(self):
        self.login_admin()
        self.client.post(reverse("admin:reservas_reserva_changelist"), {
            "action": "cancelar_reservas", "_selected_action": [self.reservas[0].pk], "index": "0",
        })
        self.reservas[0].refresh_from_db()
        self.assertEqual(self.reservas[0].estado, "CONFIRMADA")

    def test_admin_no_edita_directamente_estado_o_total_de_reserva(self):
        self.login_admin()
        respuesta = self.client.post(reverse("admin:reservas_reserva_change", args=[self.reservas[0].pk]), {
            "estado": "CANCELADA", "total": "0.00",
        })
        self.assertEqual(respuesta.status_code, 403)
        self.reservas[0].refresh_from_db()
        self.assertEqual(self.reservas[0].estado, "CONFIRMADA")
        self.assertEqual(self.reservas[0].total, Decimal("20.00"))

    def test_encuestas_admin_no_mezclan_complejos(self):
        for reserva in self.reservas:
            cancelar_reserva(reserva, self.superusuario, "Prueba de alcance")
        self.login_admin()
        respuesta = self.client.get(reverse("admin:reservas_encuesta_changelist"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.context["cl"].queryset.values_list("reserva_id", flat=True)), [self.reservas[0].pk])
        encuesta = Encuesta.objects.get(reserva=self.reservas[1])
        respuesta = self.client.get(reverse("admin:reservas_encuesta_change", args=[encuesta.pk]))
        self.assertIn(respuesta.status_code, (302, 403, 404))

    def test_formulario_complejo_permite_editar_complejo_y_cancha_propios(self):
        self.login_admin()
        datos = {
            "nombre": "Centro actualizado", "ciudad": "Quito", "direccion": "Nueva direccion", "activo": "on",
            "canchas-TOTAL_FORMS": 1, "canchas-INITIAL_FORMS": 1, "canchas-MIN_NUM_FORMS": 0, "canchas-MAX_NUM_FORMS": 1000,
            "canchas-0-id": self.canchas[0].pk, "canchas-0-complejo": self.complejo.pk,
            "canchas-0-nombre": "Cancha actualizada", "canchas-0-deporte": "FUTBOL", "canchas-0-capacidad": 12, "canchas-0-activa": "on",
        }
        respuesta = self.client.post(reverse("admin:complejos_complejo_change", args=[self.complejo.pk]), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.complejo.refresh_from_db()
        self.canchas[0].refresh_from_db()
        self.assertEqual(self.complejo.nombre, "Centro actualizado")
        self.assertEqual(self.canchas[0].nombre, "Cancha actualizada")
        self.assertEqual(self.canchas[0].capacidad, 12)

    def test_inline_no_modifica_cancha_de_otro_complejo(self):
        self.login_admin()
        respuesta = self.client.post(reverse("admin:complejos_complejo_change", args=[self.complejo.pk]), {
            "nombre": self.complejo.nombre, "ciudad": "Quito", "direccion": "Norte", "activo": "on",
            "canchas-TOTAL_FORMS": 1, "canchas-INITIAL_FORMS": 1, "canchas-MIN_NUM_FORMS": 0, "canchas-MAX_NUM_FORMS": 1000,
            "canchas-0-id": self.canchas[1].pk, "canchas-0-complejo": self.complejo.pk,
            "canchas-0-nombre": "Intrusion inline", "canchas-0-deporte": "FUTBOL", "canchas-0-capacidad": 99,
        })
        self.assertIn(respuesta.status_code, (200, 302))
        self.canchas[1].refresh_from_db()
        self.assertEqual(self.canchas[1].complejo_id, self.ajeno.pk)
        self.assertEqual(self.canchas[1].capacidad, 10)
        self.assertFalse(Cancha.objects.filter(nombre="Intrusion inline").exists())

    def test_cancelacion_administrativa_respetara_inicio_y_plazo_de_clientes(self):
        from unittest.mock import patch
        with patch("reservas.services.cancelacion.timezone.now", return_value=self.inicio - timedelta(hours=1)):
            with self.assertRaises(ValidationError):
                cancelar_reserva(self.reservas[0], self.cliente)
            cancelar_reserva(self.reservas[0], self.administrador, "Cierre por mantenimiento")
        with patch("reservas.services.cancelacion.timezone.now", return_value=self.inicio):
            with self.assertRaises(ValidationError):
                cancelar_reserva(self.reservas[1], self.plataforma, "Ya comenzo")

    def test_usuario_inactivo_no_cancela_por_servicio(self):
        self.administrador.is_active = False
        with self.assertRaises(PermissionDenied):
            cancelar_reserva(self.reservas[0], self.administrador, "Desactivado")
