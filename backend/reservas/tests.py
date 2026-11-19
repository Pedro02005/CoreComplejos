"""Pruebas del core existente: disponibilidad, tarifas y confirmación.

Ejecutar desde backend/: python manage.py test reservas -v 2
Django usa una base de datos de PRUEBAS, no la base normal.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from uuid import uuid4
from reservas.models import Recomendacion, EjecucionRegla

from reservas.services.persistencia_recomendaciones import (
    guardar_recomendaciones
)



from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from complejos.models import Bloqueo, Cancha, Complejo, HorarioAtencion, Tarifa
from reservas.models import Reserva
from reservas.services.cotizacion import cotizar_reserva



from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    PermissionDenied
)

from reservas.services.reserva import confirmar_reserva
from reservas.services.cancelacion import cancelar_reserva


from reservas.models import Encuesta, RespuestaEncuesta

from reservas.services.encuestas import generar_encuesta_cancelacion



from unittest.mock import patch

from reservas.services.encuestas import (
    generar_encuesta_experiencia
)

from reservas.services.estadisticas import (
    obtener_estadisticas_encuestas
)

from reservas.services.encuestas import (
    responder_encuesta
)
from reservas.services.historial_estadisticas import (
    obtener_estadisticas_historial
)

from reservas.services.motor_reglas import (
    evaluar_reglas,
    generar_recomendaciones
)

from reservas.models import Promocion, AsignacionPromocion


from reservas.services.asignacion_promociones import (
    asignar_promociones_personalizadas
)


from reservas.services.descuentos import calcular_descuento


from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied
)

from reservas.services.promociones_reserva import (
    cotizar_reserva_con_promocion,
    confirmar_reserva_con_promocion
)
from reservas.models import (
    Reserva,
    DetallePrecio,
    HistorialReserva,
    Encuesta,
    RespuestaEncuesta,
    Recomendacion,
    EjecucionRegla,
    Promocion,
    AsignacionPromocion,
)


ZONA = ZoneInfo("America/Guayaquil")


class CoreReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="cliente_prueba",
            email="cliente.prueba@example.com",
            password="ClaveSegura123!",
        )
        cls.complejo = Complejo.objects.create(
            nombre="Complejo de pruebas",
            ciudad="Quito",
            direccion="Direccion de pruebas",
            activo=True,
        )
        cls.cancha = Cancha.objects.create(
            complejo=cls.complejo,
            nombre="Cancha 1",
            deporte="FUTBOL",
            capacidad=10,
            activa=True,
        )

        # Fecha dinamica: siempre futura y dentro de 30 dias.
        cls.fecha = timezone.localtime(timezone.now(), ZONA).date() + timedelta(days=3)
        cls.inicio = datetime.combine(cls.fecha, time(17, 30), tzinfo=ZONA)
        cls.fin = datetime.combine(cls.fecha, time(19, 0), tzinfo=ZONA)

        HorarioAtencion.objects.create(
            cancha=cls.cancha,
            dia_semana=cls.fecha.weekday(),
            apertura=time(16, 0),
            cierre=time(21, 0),
        )
        cls.tarifa_a = Tarifa.objects.create(
            cancha=cls.cancha,
            dia_semana=cls.fecha.weekday(),
            inicio=time(16, 0),
            fin=time(18, 0),
            valor_hora=Decimal("20.00"),
            activa=True,
        )
        cls.tarifa_b = Tarifa.objects.create(
            cancha=cls.cancha,
            dia_semana=cls.fecha.weekday(),
            inicio=time(18, 0),
            fin=time(21, 0),
            valor_hora=Decimal("30.00"),
            activa=True,
        )


    def _asignacion_descuento(
        self,
        tipo="PORCENTAJE",
        valor="10.00"
    ):

        promocion = self._promocion_ejemplo(
            codigo="CALCULO10",
            tipo_descuento=tipo,
            valor_descuento=Decimal(valor),
            regla_objetivo="R01"
        )

        promocion.full_clean()
        promocion.save()

        asignacion = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            motivo_asignacion="Promoción de prueba."
        )

        asignacion.full_clean()
        asignacion.save()

        return asignacion


    def test_87_calcular_descuento_porcentaje(self):

        asignacion = self._asignacion_descuento()

        resultado = calcular_descuento(
            asignacion,
            self.usuario,
            Decimal("40.00")
        )

        self.assertEqual(
            resultado["subtotal"],
            "40.00"
        )

        self.assertEqual(
            resultado["descuento"],
            "4.00"
        )

        self.assertEqual(
            resultado["total"],
            "36.00"
        )

        # Cotizar no debe consumir la promoción
        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )


    def test_88_descuento_no_genera_total_negativo(self):

        asignacion = self._asignacion_descuento(
            tipo="MONTO_FIJO",
            valor="50.00"
        )

        resultado = calcular_descuento(
            asignacion,
            self.usuario,
            Decimal("40.00")
        )

        self.assertEqual(
            resultado["descuento"],
            "40.00"
        )

        self.assertEqual(
            resultado["total"],
            "0.00"
        )



    def test_89_no_utiliza_promocion_ajena(self):

        asignacion = self._asignacion_descuento()

        otro = get_user_model().objects.create_user(
            username="otro_descuento",
            email="otro.descuento@example.com",
            password="ClaveSegura123!"
        )

        with self.assertRaises(PermissionDenied):

            calcular_descuento(
                asignacion,
                otro,
                Decimal("40.00")
            )


    def test_90_no_utiliza_promocion_revocada(self):

        asignacion = self._asignacion_descuento()

        asignacion.estado = "REVOCADA"

        asignacion.full_clean()
        asignacion.save(update_fields=["estado"])

        with self.assertRaises(DjangoValidationError):

            calcular_descuento(
                asignacion,
                self.usuario,
                Decimal("40.00")
            )


    def test_91_no_utiliza_promocion_vencida(self):

        asignacion = self._asignacion_descuento()

        promocion = asignacion.promocion

        promocion.fecha_fin = (
            timezone.now() - timedelta(minutes=1)
        )

        promocion.save(update_fields=["fecha_fin"])

        with self.assertRaises(DjangoValidationError):

            calcular_descuento(
                asignacion,
                self.usuario,
                Decimal("40.00")
            )


    def test_92_respeta_limite_de_usos(self):

        asignacion = self._asignacion_descuento()

        promocion = asignacion.promocion
        promocion.limite_usos = 1
        promocion.save(update_fields=["limite_usos"])

        # Crear otro cliente
        otro = get_user_model().objects.create_user(
            username="cliente_promo_utilizada",
            email="promo.utilizada@example.com",
            password="ClaveSegura123!"
        )

        # Confirmar una reserva de prueba
        reserva = confirmar_reserva(
            otro,
            self.cancha,
            self.inicio,
            self.fin
        )

        # Crear asignación para el otro cliente
        utilizada = AsignacionPromocion(
            cliente=otro,
            promocion=promocion,
            motivo_asignacion="Promoción de prueba."
        )

        utilizada.full_clean()
        utilizada.save()

        # Registrar que ya utilizó la promoción
        utilizada.estado = "UTILIZADA"
        utilizada.reserva_utilizada = reserva
        utilizada.fecha_uso = timezone.now()
        utilizada.descuento_aplicado = Decimal("4.00")

        utilizada.full_clean()
        utilizada.save()

        # El límite es 1 y ya fue utilizado
        with self.assertRaises(DjangoValidationError):

            calcular_descuento(
                asignacion,
                self.usuario,
                Decimal("40.00")
            )


    def test_93_rechaza_subtotal_invalido(self):

        asignacion = self._asignacion_descuento()

        with self.assertRaises(DjangoValidationError):

            calcular_descuento(
                asignacion,
                self.usuario,
                Decimal("0.00")
            )

        with self.assertRaises(DjangoValidationError):

            calcular_descuento(
                asignacion,
                self.usuario,
                Decimal("-10.00")
            )

        with self.assertRaises(DjangoValidationError):

            calcular_descuento(
                asignacion,
                self.usuario,
                Decimal("40.001")
            )


    def _promocion_ejemplo(self, **cambios):

        ahora = timezone.now()

        datos = {
            "nombre": "Descuento por precio",
            "codigo": "PRECIO10",
            "descripcion": "Campaña de prueba.",
            "tipo_descuento": "PORCENTAJE",
            "valor_descuento": Decimal("10.00"),
            "fecha_inicio": ahora - timedelta(days=1),
            "fecha_fin": ahora + timedelta(days=7),
            "limite_usos": 50,
            "activa": True,
        }

        datos.update(cambios)

        return Promocion(**datos)

    def _preparar_cancelacion_precio(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        responder_encuesta(
            encuesta,
            self.usuario,
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO"
            }
        )

        return reserva


    def _recomendacion_ejemplo(self, **cambios):

        datos = {
            "cliente": self.usuario,
            "regla": "R01",
            "categoria": "PRECIO",
            "titulo": "Opciones económicas",
            "motivo": "Canceló por precio.",
            "accion_sugerida": "EVALUAR_DESCUENTO",
            "prioridad": 2,
            "vence_en": (
                timezone.now() + timedelta(days=7)
            ),
            "activa": True
        }

        datos.update(cambios)

        return Recomendacion(**datos)


    def _datos_base_reglas(self):

        encuestas = {
            "cancelaciones": {
                "cantidad_respuestas": 0,
                "ultima_respuesta": None
            },
            "experiencias": {
                "cantidad_respuestas": 0,
                "calificacion_promedio": None,
                "muestra_suficiente": False,
                "ultima_respuesta": None
            }
        }

        historial = {
            "reservas_finalizadas": 0,
            "cancelaciones_recientes": 0,
            "franja_preferida": None
        }

        return encuestas, historial


    def _crear_reserva_historica(
        self,
        dias_atras=10,
        hora=18,
        total="40.00"
    ):

        zona = ZoneInfo("America/Guayaquil")

        fecha = (
            timezone.localtime(
                timezone.now(),
                zona
            ).date()
            - timedelta(days=dias_atras)
        )

        inicio = datetime.combine(
            fecha,
            time(hora, 0),
            tzinfo=zona
        )

        fin = inicio + timedelta(minutes=90)

        reserva = Reserva(
            cliente=self.usuario,
            cancha=self.cancha,
            inicio=inicio,
            fin=fin,
            estado="CONFIRMADA",
            total=Decimal(total),
            clave_solicitud=uuid4(),
            cancelable_hasta=(
                inicio - timedelta(hours=12)
            )
        )

        reserva.full_clean()
        reserva.save()

        return reserva


    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(user=self.usuario)
        self.datos = {
            "cancha_id": self.cancha.pk,
            "inicio": self.inicio.isoformat(),
            "fin": self.fin.isoformat(),
        }

    def test_01_cotizacion_por_tramos(self):
        resultado = cotizar_reserva(self.cancha, self.inicio, self.fin)
        self.assertEqual(resultado["total"], "40.00")
        self.assertEqual(len(resultado["detalles"]), 2)
        self.assertEqual(resultado["detalles"][0]["subtotal"], "10.00")
        self.assertEqual(resultado["detalles"][1]["subtotal"], "30.00")

    def test_02_disponibilidad_api_incluye_horario_cotizado(self):
        respuesta = self.api.get(
            reverse("disponibilidad", kwargs={"cancha_id": self.cancha.pk}),
            {"fecha": self.fecha.isoformat(), "duracion": 90},
        )
        self.assertEqual(respuesta.status_code, 200)
        opciones = respuesta.data["opciones"]
        opcion = next((o for o in opciones if o["inicio"] == self.inicio.isoformat()), None)
        self.assertIsNotNone(opcion)
        self.assertEqual(opcion["total"], "40.00")

    def test_03_api_cotizar_no_crea_reserva(self):
        respuesta = self.api.post(reverse("cotizar"), self.datos, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["total"], "40.00")
        self.assertEqual(Reserva.objects.count(), 0)

    def test_04_confirmar_reserva_guarda_precio_y_cliente(self):
        respuesta = self.api.post(reverse("confirmar-reserva"), self.datos, format="json")
        self.assertEqual(respuesta.status_code, 201)
        reserva = Reserva.objects.get(pk=respuesta.data["id"])
        self.assertEqual(reserva.cliente_id, self.usuario.pk)
        self.assertEqual(reserva.estado, "CONFIRMADA")
        self.assertEqual(reserva.total, Decimal("40.00"))

    def test_05_reserva_ya_existente_impide_solapamiento(self):
        primera = self.api.post(reverse("confirmar-reserva"), self.datos, format="json")
        segunda = self.api.post(reverse("confirmar-reserva"), self.datos, format="json")
        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 400)
        self.assertEqual(Reserva.objects.filter(estado="CONFIRMADA").count(), 1)

    def test_06_bloqueo_mantenimiento_impide_confirmar(self):
        Bloqueo.objects.create(
            cancha=self.cancha,
            administrador=self.usuario,
            inicio=datetime.combine(self.fecha, time(17, 0), tzinfo=ZONA),
            fin=datetime.combine(self.fecha, time(18, 30), tzinfo=ZONA),
            motivo="Mantenimiento",
            activo=True,
        )
        respuesta = self.api.post(reverse("confirmar-reserva"), self.datos, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_07_rechaza_hueco_entre_tarifas(self):
        self.tarifa_b.activa = False
        self.tarifa_b.save(update_fields=["activa"])
        respuesta = self.api.post(reverse("cotizar"), self.datos, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_08_rechaza_reserva_fuera_de_horario(self):
        datos = dict(self.datos)
        datos["inicio"] = datetime.combine(self.fecha, time(21, 0), tzinfo=ZONA).isoformat()
        datos["fin"] = datetime.combine(self.fecha, time(22, 0), tzinfo=ZONA).isoformat()
        respuesta = self.api.post(reverse("confirmar-reserva"), datos, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_09_cotizacion_rechaza_intervalo_invertido(self):
        datos = dict(self.datos)
        datos["inicio"], datos["fin"] = datos["fin"], datos["inicio"]
        respuesta = self.api.post(reverse("cotizar"), datos, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_10_confirmar_exige_autenticacion(self):
        anonimo = APIClient()
        respuesta = anonimo.post(reverse("confirmar-reserva"), self.datos, format="json")
        self.assertIn(respuesta.status_code, (401, 403))
        self.assertEqual(Reserva.objects.count(), 0)

    def test_11_no_permite_reservas_pasadas(self):
        fecha_pasada = timezone.localtime(timezone.now(), ZONA).date() - timedelta(days=1)
        datos = dict(self.datos)
        datos["inicio"] = datetime.combine(fecha_pasada, time(17, 30), tzinfo=ZONA).isoformat()
        datos["fin"] = datetime.combine(fecha_pasada, time(19, 0), tzinfo=ZONA).isoformat()
        respuesta = self.api.post(reverse("cotizar"), datos, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_12_rechaza_cancha_inactiva(self):
        self.cancha.activa = False
        self.cancha.save(update_fields=["activa"])
        respuesta = self.api.post(reverse("confirmar-reserva"), self.datos, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_13_confirmacion_guarda_detalles_e_historial(self):

        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            self.datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        reserva = Reserva.objects.get(
            pk=respuesta.data["id"]
        )

        # Verificar el total de la reserva
        self.assertEqual(
            reserva.total,
            Decimal("40.00")
        )

        # Verificar los detalles de precio
        detalles = list(reserva.detalles_precio.all())

        self.assertEqual(len(detalles), 2)

        self.assertEqual(
            detalles[0].subtotal,
            Decimal("10.00")
        )

        self.assertEqual(
            detalles[1].subtotal,
            Decimal("30.00")
        )

        # Verificar el historial
        self.assertEqual(reserva.historial.count(), 1)

        evento = reserva.historial.first()

        self.assertEqual(evento.evento, "CREACION")
        self.assertEqual(evento.actor, self.usuario)
        self.assertEqual(evento.estado_nuevo, "CONFIRMADA")

        # Cambiar una tarifa no debe alterar
        # el precio histórico de la reserva
        self.tarifa_a.valor_hora = Decimal("25.00")
        self.tarifa_a.save(update_fields=["valor_hora"])

        detalles[0].refresh_from_db()

        self.assertEqual(
            detalles[0].valor_hora,
            Decimal("20.00")
        )

        self.assertEqual(
            detalles[0].subtotal,
            Decimal("10.00")
        )


    def test_14_cliente_cancela_y_libera_cancha(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(
            reserva,
            self.usuario,
            "Cambio de planes"
        )

        reserva.refresh_from_db()

        self.assertEqual(
            reserva.estado,
            "CANCELADA"
        )

        self.assertEqual(
            reserva.historial.count(),
            2
        )

        evento = reserva.historial.last()

        self.assertEqual(
            evento.evento,
            "CANCELACION"
        )

        self.assertEqual(
            evento.actor,
            self.usuario
        )

        # La cancha debe quedar disponible nuevamente
        cotizacion = cotizar_reserva(
            self.cancha,
            self.inicio,
            self.fin
        )

        self.assertEqual(
            cotizacion["total"],
            "40.00"
        )


    def test_15_no_permite_cancelar_dos_veces(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(
            reserva,
            self.usuario
        )

        with self.assertRaises(DjangoValidationError):

            cancelar_reserva(
                reserva,
                self.usuario
            )

        self.assertEqual(
            reserva.historial.filter(
                evento="CANCELACION"
            ).count(),
            1
        )


    def test_16_otro_cliente_no_puede_cancelar(self):

        otro_usuario = get_user_model().objects.create_user(
            username="otro_cliente",
            email="otro.cliente@example.com",
            password="ClaveSegura123!"
        )

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        with self.assertRaises(PermissionDenied):

            cancelar_reserva(
                reserva,
                otro_usuario
            )

        reserva.refresh_from_db()

        self.assertEqual(
            reserva.estado,
            "CONFIRMADA"
        )



    def test_17_api_permite_cancelar_reserva(self):

        # Primero confirmar una reserva
        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            self.datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        reserva_id = respuesta.data["id"]

        # Cancelar mediante la API
        respuesta = self.api.post(
            reverse(
                "cancelar-reserva",
                kwargs={"reserva_id": reserva_id}
            ),
            {"motivo": "Cambio de planes"},
            format="json"
        )

        self.assertEqual(respuesta.status_code, 200)

        reserva = Reserva.objects.get(pk=reserva_id)

        self.assertEqual(
            reserva.estado,
            "CANCELADA"
        )

        self.assertEqual(
            reserva.historial.filter(
                evento="CANCELACION"
            ).count(),
            1
        )


    def test_18_api_no_permite_cancelar_dos_veces(self):

        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            self.datos,
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        reserva_id = respuesta.data["id"]

        url = reverse(
            "cancelar-reserva",
            kwargs={"reserva_id": reserva_id}
        )

        primera = self.api.post(
            url,
            {"motivo": "Cambio de planes"},
            format="json"
        )

        segunda = self.api.post(
            url,
            {"motivo": "Otra cancelación"},
            format="json"
        )

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 400)

        reserva = Reserva.objects.get(pk=reserva_id)

        self.assertEqual(
            reserva.historial.filter(
                evento="CANCELACION"
            ).count(),
            1
        )

    def test_19_listar_reservas_del_cliente(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        respuesta = self.api.get(
            reverse("confirmar-reserva")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(
            respuesta.data[0]["id"],
            reserva.id
        )


    def test_20_consultar_detalle_reserva(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        respuesta = self.api.get(
            reverse(
                "detalle-reserva",
                kwargs={"reserva_id": reserva.id}
            )
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta.data["total"],
            "40.00"
        )

        self.assertEqual(
            len(respuesta.data["detalles_precio"]),
            2
        )

        self.assertEqual(
            len(respuesta.data["historial"]),
            1
        )

        self.assertEqual(
            respuesta.data["historial"][0]["evento"],
            "CREACION"
        )


    def test_21_cliente_no_ve_reservas_ajenas(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        otro = get_user_model().objects.create_user(
            username="cliente_ajeno",
            email="ajeno@example.com",
            password="ClaveSegura123!"
        )

        self.api.force_authenticate(user=otro)

        listado = self.api.get(
            reverse("confirmar-reserva")
        )

        detalle = self.api.get(
            reverse(
                "detalle-reserva",
                kwargs={"reserva_id": reserva.id}
            )
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 0)
        self.assertEqual(detalle.status_code, 404)


    def test_22_superusuario_puede_consultar_reservas(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        administrador = get_user_model().objects.create_superuser(
            username="admin_prueba",
            email="admin.prueba@example.com",
            password="ClaveSegura123!"
        )

        self.api.force_authenticate(user=administrador)

        listado = self.api.get(
            reverse("confirmar-reserva")
        )

        detalle = self.api.get(
            reverse(
                "detalle-reserva",
                kwargs={"reserva_id": reserva.id}
            )
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)
        self.assertEqual(detalle.status_code, 200)


    def test_23_reserva_cancelada_sigue_en_historial(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(
            reserva,
            self.usuario,
            "Cambio de planes"
        )

        respuesta = self.api.get(
            reverse(
                "detalle-reserva",
                kwargs={"reserva_id": reserva.id}
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["estado"],
            "CANCELADA"
        )
        self.assertEqual(
            len(respuesta.data["historial"]),
            2
        )



    def test_24_encuesta_cancelacion_valida(self):

        # 1. Confirmar una reserva
        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # 2. Cancelar la reserva
        cancelar_reserva(reserva, self.usuario)

        # 3. Obtener la encuesta generada automáticamente
        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        # 4. Verificar que aún no tiene respuesta
        self.assertFalse(
            RespuestaEncuesta.objects.filter(
                encuesta=encuesta
            ).exists()
        )

        # 5. Crear una respuesta
        respuesta = RespuestaEncuesta(
            encuesta=encuesta,
            motivo_cancelacion="PRECIO",
            hubiera_evitado="DESCUENTO",
            comentario="El precio era elevado."
        )

        respuesta.full_clean()
        respuesta.save()

        # 6. Comprobar que se guardó correctamente
        self.assertEqual(
            encuesta.respuesta.motivo_cancelacion,
            "PRECIO"
        )

        self.assertEqual(
            encuesta.respuesta.hubiera_evitado,
            "DESCUENTO"
        )


    def test_25_no_encuesta_cancelacion_sin_cancelar(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        encuesta = Encuesta(
            reserva=reserva,
            tipo="CANCELACION"
        )

        with self.assertRaises(DjangoValidationError):
            encuesta.full_clean()



    def test_26_no_duplicar_encuestas(self):

        # 1. Confirmar una reserva
        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # 2. Cancelar: genera automáticamente una encuesta
        cancelar_reserva(reserva, self.usuario)

        # 3. Comprobar que ya existe una encuesta
        primera = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        self.assertIsNotNone(primera.id)

        # 4. Intentar crear otra encuesta del mismo tipo
        duplicada = Encuesta(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        # 5. Django debe rechazar el duplicado
        with self.assertRaises(DjangoValidationError):
            duplicada.full_clean()

        # 6. Verificar que solo existe una encuesta
        self.assertEqual(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_CANCELACION
            ).count(),
            1
        )



    def test_27_experiencia_requiere_horario_terminado(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        encuesta = Encuesta(
            reserva=reserva,
            tipo="EXPERIENCIA"
        )

        with self.assertRaises(DjangoValidationError):
            encuesta.full_clean()


    def test_28_cancelacion_genera_encuesta_automatica(self):

        # Confirmar una reserva
        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # Cancelar la reserva
        cancelar_reserva(
            reserva,
            self.usuario,
            "Cambio de planes"
        )

        # Verificar que la encuesta se creó
        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo="CANCELACION"
        )

        self.assertIsNotNone(encuesta.id)

        # La encuesta todavía no debe tener respuesta
        self.assertFalse(
            RespuestaEncuesta.objects.filter(
                encuesta=encuesta
            ).exists()
        )


    def test_29_no_duplica_encuesta_cancelacion(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(
            reserva,
            self.usuario
        )

        # Ejecutar nuevamente el generador
        primera = generar_encuesta_cancelacion(reserva)
        segunda = generar_encuesta_cancelacion(reserva)

        # Debe devolver la misma encuesta
        self.assertEqual(
            primera.id,
            segunda.id
        )

        self.assertEqual(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo="CANCELACION"
            ).count(),
            1
        )


    def test_30_no_genera_encuesta_sin_cancelar(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # No debe funcionar con una reserva confirmada
        with self.assertRaises(DjangoValidationError):

            generar_encuesta_cancelacion(reserva)

        self.assertFalse(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo="CANCELACION"
            ).exists()
        )



    def test_31_genera_encuesta_experiencia(self):

        # Crear una reserva futura
        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # Simular que el tiempo avanzó
        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "reservas.services.encuestas.timezone.now",
            return_value=fecha_simulada
        ):

            encuesta = generar_encuesta_experiencia(
                reserva
            )

        # Verificar que se generó correctamente
        self.assertEqual(
            encuesta.tipo,
            Encuesta.TIPO_EXPERIENCIA
        )

        self.assertEqual(
            encuesta.reserva,
            reserva
        )

        # Todavía no debe tener una respuesta
        self.assertFalse(
            RespuestaEncuesta.objects.filter(
                encuesta=encuesta
            ).exists()
        )


    def test_32_no_genera_experiencia_antes_del_fin(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        with self.assertRaises(DjangoValidationError):

            generar_encuesta_experiencia(reserva)

        self.assertFalse(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_EXPERIENCIA
            ).exists()
        )


    def test_33_cancelada_no_genera_experiencia(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(
            reserva,
            self.usuario,
            "Cambio de planes"
        )

        # Simular que terminó el horario original
        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "reservas.services.encuestas.timezone.now",
            return_value=fecha_simulada
        ):

            with self.assertRaises(DjangoValidationError):
                generar_encuesta_experiencia(reserva)

        self.assertFalse(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_EXPERIENCIA
            ).exists()
        )

        # La encuesta de cancelación debe conservarse
        self.assertTrue(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_CANCELACION
            ).exists()
        )


    def test_34_no_duplica_encuesta_experiencia(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "reservas.services.encuestas.timezone.now",
            return_value=fecha_simulada
        ):

            primera = generar_encuesta_experiencia(
                reserva
            )

            segunda = generar_encuesta_experiencia(
                reserva
            )

        self.assertEqual(
            primera.id,
            segunda.id
        )

        self.assertEqual(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_EXPERIENCIA
            ).count(),
            1
        )


    def test_35_no_hay_experiencia_pendiente_antes_del_fin(self):

        confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        respuesta = self.api.get(
            reverse("encuestas-pendientes")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 0)


    def test_36_api_genera_experiencia_pendiente(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "reservas.services.encuestas.timezone.now",
            return_value=fecha_simulada
        ):
            respuesta = self.api.get(
                reverse("encuestas-pendientes")
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 1)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_EXPERIENCIA
        )

        self.assertEqual(
            respuesta.data[0]["id"],
            encuesta.id
        )

        self.assertEqual(
            respuesta.data[0]["tipo"],
            "EXPERIENCIA"
        )


    def test_37_consultar_dos_veces_no_duplica(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "reservas.services.encuestas.timezone.now",
            return_value=fecha_simulada
        ):

            primera = self.api.get(
                reverse("encuestas-pendientes")
            )

            segunda = self.api.get(
                reverse("encuestas-pendientes")
            )

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 200)

        self.assertEqual(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_EXPERIENCIA
            ).count(),
            1
        )


    def test_38_cliente_no_ve_encuestas_ajenas(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        otro = get_user_model().objects.create_user(
            username="cliente_encuestas_ajeno",
            email="encuestas.ajeno@example.com",
            password="ClaveSegura123!"
        )

        self.api.force_authenticate(user=otro)

        respuesta = self.api.get(
            reverse("encuestas-pendientes")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 0)



    def test_39_encuesta_respondida_no_aparece_pendiente(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        # Antes de responder, debe aparecer pendiente
        primera = self.api.get(
            reverse("encuestas-pendientes")
        )

        self.assertEqual(len(primera.data), 1)

        # Registrar una respuesta válida
        respuesta_encuesta = RespuestaEncuesta(
            encuesta=encuesta,
            motivo_cancelacion="PRECIO",
            hubiera_evitado="DESCUENTO"
        )

        respuesta_encuesta.full_clean()
        respuesta_encuesta.save()

        # Después de responder, ya no aparece
        segunda = self.api.get(
            reverse("encuestas-pendientes")
        )

        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(len(segunda.data), 0)


    def test_40_api_responde_encuesta_cancelacion(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        respuesta = self.api.post(
            reverse(
                "responder-encuesta",
                kwargs={"encuesta_id": encuesta.id}
            ),
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO",
                "comentario": "Precio elevado."
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, 201)

        guardada = RespuestaEncuesta.objects.get(
            encuesta=encuesta
        )

        self.assertEqual(
            guardada.motivo_cancelacion, "PRECIO"
        )
        self.assertEqual(
            guardada.hubiera_evitado, "DESCUENTO"
        )

        pendientes = self.api.get(
            reverse("encuestas-pendientes")
        )

        self.assertEqual(len(pendientes.data), 0)


    def test_41_no_permite_responder_dos_veces(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        url = reverse(
            "responder-encuesta",
            kwargs={"encuesta_id": encuesta.id}
        )

        datos = {
            "motivo_cancelacion": "PRECIO",
            "hubiera_evitado": "DESCUENTO"
        }

        primera = self.api.post(
            url, datos, format="json"
        )

        segunda = self.api.post(
            url, datos, format="json"
        )

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 400)

        self.assertEqual(
            RespuestaEncuesta.objects.filter(
                encuesta=encuesta
            ).count(),
            1
        )


    def test_42_no_responde_encuesta_ajena(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        otro = get_user_model().objects.create_user(
            username="otro_encuestado",
            email="otro.encuestado@example.com",
            password="ClaveSegura123!"
        )

        self.api.force_authenticate(user=otro)

        respuesta = self.api.post(
            reverse(
                "responder-encuesta",
                kwargs={"encuesta_id": encuesta.id}
            ),
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO"
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, 404)

        self.assertFalse(
            RespuestaEncuesta.objects.filter(
                encuesta=encuesta
            ).exists()
        )


    def test_43_rechaza_campos_de_tipo_incorrecto(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        respuesta = self.api.post(
            reverse(
                "responder-encuesta",
                kwargs={"encuesta_id": encuesta.id}
            ),
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO",
                "calificacion": 4
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, 400)

        self.assertFalse(
            RespuestaEncuesta.objects.filter(
                encuesta=encuesta
            ).exists()
        )


    def test_44_api_responde_encuesta_experiencia(self):

        reserva = confirmar_reserva(
            self.usuario, self.cancha,
            self.inicio, self.fin
        )

        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "django.utils.timezone.now",
            return_value=fecha_simulada
        ):

            encuesta = generar_encuesta_experiencia(
                reserva
            )

            respuesta = self.api.post(
                reverse(
                    "responder-encuesta",
                    kwargs={"encuesta_id": encuesta.id}
                ),
                {
                    "calificacion": 2,
                    "volveria_reservar": False,
                    "aspecto_mejorar": "INSTALACIONES",
                    "comentario": "Necesita mantenimiento."
                },
                format="json"
            )

        self.assertEqual(respuesta.status_code, 201)

        guardada = RespuestaEncuesta.objects.get(
            encuesta=encuesta
        )

        self.assertEqual(guardada.calificacion, 2)

        self.assertIs(
            guardada.volveria_reservar,
            False
        )

        self.assertEqual(
            guardada.aspecto_mejorar,
            "INSTALACIONES"
        )


    def test_45_admin_visualiza_encuesta_y_respuesta(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        respuesta = RespuestaEncuesta(
            encuesta=encuesta,
            motivo_cancelacion="PRECIO",
            hubiera_evitado="DESCUENTO",
            comentario="El precio era elevado."
        )

        respuesta.full_clean()
        respuesta.save()

        administrador = get_user_model().objects.create_superuser(
            username="admin_encuestas",
            email="admin.encuestas@example.com",
            password="ClaveSegura123!"
        )

        self.client.force_login(administrador)

        # Comprobar listado del Admin
        listado = self.client.get(
            reverse("admin:reservas_encuesta_changelist")
        )

        self.assertEqual(listado.status_code, 200)

        # Comprobar detalle
        detalle = self.client.get(
            reverse(
                "admin:reservas_encuesta_change",
                args=[encuesta.id]
            )
        )

        self.assertEqual(detalle.status_code, 200)

        self.assertContains(
            detalle,
            "El precio era elevado."
        )


    def test_46_cliente_no_accede_admin_encuestas(self):

        self.client.force_login(self.usuario)

        respuesta = self.client.get(
            reverse("admin:reservas_encuesta_changelist")
        )

        # Un cliente sin permisos de staff
        # será redirigido al login del Admin
        self.assertEqual(respuesta.status_code, 302)


    def test_47_estadisticas_sin_respuestas(self):

        datos = obtener_estadisticas_encuestas(
            self.usuario
        )

        self.assertEqual(
            datos["cancelaciones"]["cantidad_respuestas"],
            0
        )

        self.assertEqual(
            datos["experiencias"]["cantidad_respuestas"],
            0
        )

        self.assertIsNone(
            datos["experiencias"]["calificacion_promedio"]
        )


    def test_48_estadisticas_cancelacion(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        responder_encuesta(
            encuesta,
            self.usuario,
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO"
            }
        )

        datos = obtener_estadisticas_encuestas(
            self.usuario
        )

        cancelaciones = datos["cancelaciones"]

        self.assertEqual(
            cancelaciones["cantidad_respuestas"],
            1
        )

        self.assertEqual(
            cancelaciones["motivos"][0]["motivo_cancelacion"],
            "PRECIO"
        )

        self.assertEqual(
            cancelaciones["motivos"][0]["cantidad"],
            1
        )

        self.assertEqual(
            cancelaciones["ultima_respuesta"]["hubiera_evitado"],
            "DESCUENTO"
        )


    def test_49_estadisticas_experiencia(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        fecha_simulada = self.fin + timedelta(minutes=1)

        with patch(
            "django.utils.timezone.now",
            return_value=fecha_simulada
        ):

            encuesta = generar_encuesta_experiencia(
                reserva
            )

            responder_encuesta(
                encuesta,
                self.usuario,
                {
                    "calificacion": 2,
                    "volveria_reservar": False,
                    "aspecto_mejorar": "INSTALACIONES"
                }
            )

            datos = obtener_estadisticas_encuestas(
                self.usuario
            )

        experiencias = datos["experiencias"]

        self.assertEqual(
            experiencias["cantidad_respuestas"],
            1
        )

        self.assertEqual(
            experiencias["calificacion_promedio"],
            2.0
        )

        self.assertEqual(
            experiencias["volveria_reservar_si"],
            0
        )

        self.assertFalse(
            experiencias["muestra_suficiente"]
        )



    def test_50_estadisticas_no_mezclan_clientes(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(reserva, self.usuario)

        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        responder_encuesta(
            encuesta,
            self.usuario,
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO"
            }
        )

        otro = get_user_model().objects.create_user(
            username="otro_estadisticas",
            email="estadisticas@example.com",
            password="ClaveSegura123!"
        )

        datos = obtener_estadisticas_encuestas(otro)

        self.assertEqual(
            datos["cancelaciones"]["cantidad_respuestas"],
            0
        )

        self.assertEqual(
            datos["experiencias"]["cantidad_respuestas"],
            0
        )



    def test_51_historial_sin_reservas(self):

        datos = obtener_estadisticas_historial(
            self.usuario
        )

        self.assertEqual(
            datos["reservas_finalizadas"],
            0
        )

        self.assertIsNone(
            datos["deporte_favorito"]
        )

        self.assertIsNone(
            datos["precio_hora_referencia"]
        )

        self.assertFalse(
            datos["muestra_suficiente"]
        )


    def test_52_historial_calcula_preferencias(self):

        self._crear_reserva_historica(
            dias_atras=10,
            hora=18,
            total="40.00"
        )

        datos = obtener_estadisticas_historial(
            self.usuario
        )

        self.assertEqual(
            datos["reservas_finalizadas"],
            1
        )

        self.assertEqual(
            datos["deporte_favorito"]["codigo"],
            self.cancha.deporte
        )

        self.assertEqual(
            datos["franja_preferida"]["codigo"],
            "NOCHE"
        )

        self.assertEqual(
            datos["precio_hora_referencia"],
            "26.67"
        )


    def test_53_historial_respeta_90_dias(self):

        self._crear_reserva_historica(
            dias_atras=100
        )

        datos = obtener_estadisticas_historial(
            self.usuario,
            dias=90
        )

        self.assertEqual(
            datos["reservas_finalizadas"],
            0
        )


    def test_54_historial_cuenta_cancelaciones(self):

        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        cancelar_reserva(
            reserva,
            self.usuario,
            "Cambio de planes"
        )

        datos = obtener_estadisticas_historial(
            self.usuario
        )

        self.assertEqual(
            datos["cancelaciones_recientes"],
            1
        )

        self.assertEqual(
            datos["reservas_finalizadas"],
            0
        )


    def test_55_historial_no_mezcla_clientes(self):

        self._crear_reserva_historica(
            dias_atras=10
        )

        otro = get_user_model().objects.create_user(
            username="cliente_historial_ajeno",
            email="historial.ajeno@example.com",
            password="ClaveSegura123!"
        )

        datos = obtener_estadisticas_historial(
            otro
        )

        self.assertEqual(
            datos["reservas_finalizadas"],
            0
        )

        self.assertIsNone(
            datos["deporte_favorito"]
        )


    def test_56_regla_precio(self):

        encuestas, historial = self._datos_base_reglas()

        encuestas["cancelaciones"]["ultima_respuesta"] = {
            "motivo_cancelacion": "PRECIO",
            "hubiera_evitado": "DESCUENTO"
        }

        resultado = evaluar_reglas(
            encuestas,
            historial
        )

        self.assertEqual(len(resultado), 1)

        self.assertEqual(
            resultado[0]["regla"],
            "R01"
        )

        self.assertEqual(
            resultado[0]["accion_sugerida"],
            "EVALUAR_DESCUENTO"
        )


    def test_57_regla_horario(self):

        encuestas, historial = self._datos_base_reglas()

        encuestas["cancelaciones"]["ultima_respuesta"] = {
            "motivo_cancelacion": "HORARIO",
            "hubiera_evitado": "CAMBIO_HORARIO"
        }

        historial["franja_preferida"] = {
            "codigo": "NOCHE",
            "cantidad": 4
        }

        resultado = evaluar_reglas(
            encuestas,
            historial
        )

        self.assertEqual(len(resultado), 1)

        self.assertEqual(
            resultado[0]["regla"],
            "R02"
        )

        self.assertIn(
            "la noche",
            resultado[0]["motivo"]
        )


    def test_58_regla_mala_experiencia(self):

        encuestas, historial = self._datos_base_reglas()

        encuestas["experiencias"]["ultima_respuesta"] = {
            "calificacion": 2,
            "volveria_reservar": False,
            "aspecto_mejorar": "INSTALACIONES"
        }

        resultado = evaluar_reglas(
            encuestas,
            historial
        )

        self.assertEqual(len(resultado), 1)

        self.assertEqual(
            resultado[0]["regla"],
            "R04"
        )

        self.assertEqual(
            resultado[0]["accion_sugerida"],
            "BUSCAR_OTRA_CANCHA"
        )


    def test_59_regla_fidelizacion(self):

        encuestas, historial = self._datos_base_reglas()

        historial["reservas_finalizadas"] = 5

        encuestas["experiencias"].update({
            "cantidad_respuestas": 3,
            "calificacion_promedio": 4.67,
            "muestra_suficiente": True
        })

        resultado = evaluar_reglas(
            encuestas,
            historial
        )

        self.assertEqual(len(resultado), 1)

        self.assertEqual(
            resultado[0]["regla"],
            "R05"
        )

        self.assertEqual(
            resultado[0]["accion_sugerida"],
            "EVALUAR_BENEFICIO_FIDELIDAD"
        )


    def test_60_sin_datos_no_inventa_recomendaciones(self):

        encuestas, historial = self._datos_base_reglas()

        resultado = evaluar_reglas(
            encuestas,
            historial
        )

        self.assertEqual(resultado, [])



    def test_61_motor_usa_respuestas_reales(self):

        # 1. Confirmar una reserva
        reserva = confirmar_reserva(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # 2. Cancelarla
        cancelar_reserva(
            reserva,
            self.usuario
        )

        # 3. Recuperar la encuesta automática
        encuesta = Encuesta.objects.get(
            reserva=reserva,
            tipo=Encuesta.TIPO_CANCELACION
        )

        # 4. Responderla
        responder_encuesta(
            encuesta,
            self.usuario,
            {
                "motivo_cancelacion": "PRECIO",
                "hubiera_evitado": "DESCUENTO"
            }
        )

        # 5. Ejecutar el motor con datos reales
        resultado = generar_recomendaciones(
            self.usuario
        )

        reglas = [
            recomendacion["regla"]
            for recomendacion in resultado["recomendaciones"]
        ]

        # 6. Verificar que se active R01
        self.assertIn("R01", reglas)

        self.assertEqual(
            resultado["cantidad_recomendaciones"],
            len(reglas)
        )


    def test_62_guardar_recomendacion(self):

        recomendacion = self._recomendacion_ejemplo()

        recomendacion.full_clean()
        recomendacion.save()

        self.assertIsNotNone(recomendacion.id)

        self.assertEqual(
            recomendacion.regla,
            "R01"
        )

        self.assertEqual(
            Recomendacion.objects.filter(
                cliente=self.usuario,
                activa=True
            ).count(),
            1
        )


    def test_63_rechaza_recomendacion_vencida(self):

        recomendacion = self._recomendacion_ejemplo(
            vence_en=timezone.now() - timedelta(days=1)
        )

        with self.assertRaises(DjangoValidationError):
            recomendacion.full_clean()


    def test_64_rechaza_prioridad_invalida(self):

        recomendacion = self._recomendacion_ejemplo(
            prioridad=0
        )

        with self.assertRaises(DjangoValidationError):
            recomendacion.full_clean()



    def test_65_registrar_regla_cumplida(self):

        recomendacion = self._recomendacion_ejemplo()

        recomendacion.full_clean()
        recomendacion.save()

        ejecucion = EjecucionRegla(
            cliente=self.usuario,
            regla="R01",
            cumplida=True,
            detalle="Cancelación por precio y descuento.",
            recomendacion=recomendacion
        )

        ejecucion.full_clean()
        ejecucion.save()

        self.assertIsNotNone(ejecucion.id)

        self.assertTrue(ejecucion.cumplida)

        self.assertEqual(
            ejecucion.recomendacion,
            recomendacion
        )



    def test_66_registrar_regla_no_cumplida(self):

        ejecucion = EjecucionRegla(
            cliente=self.usuario,
            regla="R02",
            cumplida=False,
            detalle="No existen problemas de horario.",
            recomendacion=None
        )

        ejecucion.full_clean()
        ejecucion.save()

        self.assertFalse(ejecucion.cumplida)

        self.assertIsNone(ejecucion.recomendacion)



    def test_67_rechaza_recomendacion_de_otro_cliente(self):

        recomendacion = self._recomendacion_ejemplo()
        recomendacion.full_clean()
        recomendacion.save()

        otro = get_user_model().objects.create_user(
            username="otro_recomendaciones",
            email="otro.recomendaciones@example.com",
            password="ClaveSegura123!"
        )

        ejecucion = EjecucionRegla(
            cliente=otro,
            regla="R01",
            cumplida=True,
            detalle="Intento de relación con otro cliente.",
            recomendacion=recomendacion
        )

        with self.assertRaises(DjangoValidationError):
            ejecucion.full_clean()



    def test_68_rechaza_regla_incorrecta(self):

        recomendacion = self._recomendacion_ejemplo(
            regla="R01"
        )

        recomendacion.full_clean()
        recomendacion.save()

        ejecucion = EjecucionRegla(
            cliente=self.usuario,
            regla="R02",
            cumplida=True,
            detalle="La regla no corresponde.",
            recomendacion=recomendacion
        )

        with self.assertRaises(DjangoValidationError):
            ejecucion.full_clean()



    def test_69_registra_reglas_sin_datos(self):

        resultado = guardar_recomendaciones(
            self.usuario
        )

        self.assertEqual(
            resultado["nuevas"],
            0
        )

        self.assertEqual(
            len(resultado["recomendaciones"]),
            0
        )

        self.assertEqual(
            EjecucionRegla.objects.filter(
                cliente=self.usuario
            ).count(),
            4
        )

        self.assertEqual(
            EjecucionRegla.objects.filter(
                cliente=self.usuario,
                cumplida=True
            ).count(),
            0
        )


    def test_70_persistir_regla_precio(self):

        self._preparar_cancelacion_precio()

        resultado = guardar_recomendaciones(
            self.usuario
        )

        self.assertEqual(resultado["nuevas"], 1)

        self.assertEqual(
            resultado["ejecuciones_registradas"],
            4
        )

        recomendacion = Recomendacion.objects.get(
            cliente=self.usuario,
            regla="R01",
            activa=True
        )

        self.assertEqual(
            recomendacion.accion_sugerida,
            "EVALUAR_DESCUENTO"
        )

        ejecucion = EjecucionRegla.objects.get(
            cliente=self.usuario,
            regla="R01",
            cumplida=True
        )

        self.assertEqual(
            ejecucion.recomendacion,
            recomendacion
        )



    def test_71_no_duplica_recomendaciones(self):

        self._preparar_cancelacion_precio()

        primera = guardar_recomendaciones(
            self.usuario
        )

        segunda = guardar_recomendaciones(
            self.usuario
        )

        self.assertEqual(primera["nuevas"], 1)
        self.assertEqual(segunda["nuevas"], 0)

        self.assertEqual(
            Recomendacion.objects.filter(
                cliente=self.usuario,
                regla="R01",
                activa=True
            ).count(),
            1
        )

        # Dos ejecuciones del motor: 4 + 4
        self.assertEqual(
            EjecucionRegla.objects.filter(
                cliente=self.usuario
            ).count(),
            8
        )



    def test_72_reemplaza_recomendacion_vencida(self):

        self._preparar_cancelacion_precio()

        guardar_recomendaciones(self.usuario)

        anterior = Recomendacion.objects.get(
            cliente=self.usuario,
            regla="R01"
        )

        # Simular que la recomendación venció
        anterior.vence_en = (
            timezone.now() - timedelta(minutes=1)
        )

        anterior.save(
            update_fields=["vence_en"]
        )

        resultado = guardar_recomendaciones(
            self.usuario
        )

        anterior.refresh_from_db()

        self.assertFalse(anterior.activa)

        self.assertEqual(resultado["nuevas"], 1)

        self.assertEqual(
            Recomendacion.objects.filter(
                cliente=self.usuario,
                regla="R01",
                activa=True
            ).count(),
            1
        )



    def test_73_desactiva_recomendacion_no_vigente(self):

        self._preparar_cancelacion_precio()

        guardar_recomendaciones(self.usuario)

        recomendacion = Recomendacion.objects.get(
            cliente=self.usuario,
            regla="R01"
        )

        # Simular una nueva evaluación sin reglas cumplidas
        resultado_vacio = {
            "periodo_dias": 90,
            "cantidad_recomendaciones": 0,
            "recomendaciones": []
        }

        with patch(
            "reservas.services.persistencia_recomendaciones.generar_recomendaciones",
            return_value=resultado_vacio
        ):
            guardar_recomendaciones(self.usuario)

        recomendacion.refresh_from_db()

        self.assertFalse(recomendacion.activa)

        self.assertEqual(
            Recomendacion.objects.filter(
                cliente=self.usuario,
                activa=True
            ).count(),
            0
        )


    def test_74_crear_promocion(self):

        promocion = self._promocion_ejemplo()

        promocion.full_clean()
        promocion.save()

        self.assertIsNotNone(promocion.id)

        self.assertEqual(
            promocion.valor_descuento,
            Decimal("10.00")
        )


    def test_75_rechaza_porcentaje_invalido(self):

        promocion = self._promocion_ejemplo(
            valor_descuento=Decimal("120.00")
        )

        with self.assertRaises(DjangoValidationError):
            promocion.full_clean()


    def test_76_rechaza_fechas_promocion_invalidas(self):

        ahora = timezone.now()

        promocion = self._promocion_ejemplo(
            fecha_inicio=ahora + timedelta(days=10),
            fecha_fin=ahora + timedelta(days=5)
        )

        with self.assertRaises(DjangoValidationError):
            promocion.full_clean()


    def test_77_asignar_promocion(self):

        promocion = self._promocion_ejemplo()
        promocion.full_clean()
        promocion.save()

        asignacion = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            motivo_asignacion="Campaña de bienvenida."
        )

        asignacion.full_clean()
        asignacion.save()

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )

        self.assertEqual(
            asignacion.descuento_aplicado,
            Decimal("0.00")
        )


    def test_78_no_duplicar_asignaciones(self):

        promocion = self._promocion_ejemplo()
        promocion.full_clean()
        promocion.save()

        primera = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            motivo_asignacion="Campaña inicial."
        )

        primera.full_clean()
        primera.save()

        duplicada = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            motivo_asignacion="Asignación duplicada."
        )

        with self.assertRaises(DjangoValidationError):
            duplicada.full_clean()



    def test_79_rechaza_recomendacion_ajena(self):

        otro = get_user_model().objects.create_user(
            username="cliente_promo_ajeno",
            email="promo.ajeno@example.com",
            password="ClaveSegura123!"
        )

        recomendacion = self._recomendacion_ejemplo(
            cliente=otro
        )

        recomendacion.full_clean()
        recomendacion.save()

        promocion = self._promocion_ejemplo()
        promocion.full_clean()
        promocion.save()

        asignacion = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            recomendacion=recomendacion
        )

        with self.assertRaises(DjangoValidationError):
            asignacion.full_clean()



    def test_80_rechaza_uso_sin_reserva(self):

        promocion = self._promocion_ejemplo()
        promocion.full_clean()
        promocion.save()

        asignacion = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            motivo_asignacion="Promoción de prueba.",
            estado="UTILIZADA"
        )

        with self.assertRaises(DjangoValidationError):
            asignacion.full_clean()



    def test_81_no_asignar_promocion_inactiva(self):

        promocion = self._promocion_ejemplo(
            activa=False
        )

        promocion.full_clean()
        promocion.save()

        asignacion = AsignacionPromocion(
            cliente=self.usuario,
            promocion=promocion,
            motivo_asignacion="Campaña inactiva."
        )

        with self.assertRaises(DjangoValidationError):
            asignacion.full_clean()



    def test_82_asigna_promocion_por_precio(self):

        # Preparar una cancelación que active R01
        self._preparar_cancelacion_precio()

        # Crear una campaña compatible
        promocion = self._promocion_ejemplo(
            regla_objetivo="R01"
        )

        promocion.full_clean()
        promocion.save()

        # Ejecutar asignación automática
        resultado = asignar_promociones_personalizadas(
            self.usuario
        )

        self.assertEqual(resultado["nuevas"], 1)

        asignacion = AsignacionPromocion.objects.get(
            cliente=self.usuario,
            promocion=promocion
        )

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )

        self.assertEqual(
            asignacion.recomendacion.regla,
            "R01"
        )


    def test_83_no_inventa_promociones(self):

        self._preparar_cancelacion_precio()

        # No creamos ninguna campaña
        resultado = asignar_promociones_personalizadas(
            self.usuario
        )

        self.assertEqual(resultado["nuevas"], 0)

        self.assertIn(
            "R01",
            resultado["reglas_sin_campana"]
        )

        self.assertEqual(
            AsignacionPromocion.objects.count(),
            0
        )


    def test_84_no_duplica_promociones(self):

        self._preparar_cancelacion_precio()

        promocion = self._promocion_ejemplo(
            regla_objetivo="R01"
        )

        promocion.full_clean()
        promocion.save()

        primera = asignar_promociones_personalizadas(
            self.usuario
        )

        segunda = asignar_promociones_personalizadas(
            self.usuario
        )

        self.assertEqual(primera["nuevas"], 1)
        self.assertEqual(segunda["nuevas"], 0)

        self.assertEqual(
            AsignacionPromocion.objects.filter(
                cliente=self.usuario,
                promocion=promocion
            ).count(),
            1
        )


    def test_85_no_asigna_campana_de_otra_regla(self):

        self._preparar_cancelacion_precio()

        # Campaña para fidelización, no para precio
        promocion = self._promocion_ejemplo(
            regla_objetivo="R05"
        )

        promocion.full_clean()
        promocion.save()

        resultado = asignar_promociones_personalizadas(
            self.usuario
        )

        self.assertEqual(resultado["nuevas"], 0)

        self.assertFalse(
            AsignacionPromocion.objects.filter(
                cliente=self.usuario
            ).exists()
        )


    def test_86_no_asigna_promociones_no_vigentes(self):

        self._preparar_cancelacion_precio()

        ahora = timezone.now()

        # Campaña desactivada
        inactiva = self._promocion_ejemplo(
            codigo="INACTIVA10",
            regla_objetivo="R01",
            activa=False
        )

        inactiva.full_clean()
        inactiva.save()

        # Campaña que todavía no comienza
        futura = self._promocion_ejemplo(
            codigo="FUTURA10",
            regla_objetivo="R01",
            fecha_inicio=ahora + timedelta(days=2),
            fecha_fin=ahora + timedelta(days=10)
        )

        futura.full_clean()
        futura.save()

        resultado = asignar_promociones_personalizadas(
            self.usuario
        )

        self.assertEqual(resultado["nuevas"], 0)

        self.assertFalse(
            AsignacionPromocion.objects.filter(
                cliente=self.usuario
            ).exists()
        )


    def test_94_cotizar_con_promocion(self):

        asignacion = self._asignacion_descuento()

        original = cotizar_reserva(
            self.cancha,
            self.inicio,
            self.fin
        )

        resultado = cotizar_reserva_con_promocion(
            self.cancha,
            self.inicio,
            self.fin,
            cliente=self.usuario,
            asignacion_id=asignacion.id
        )

        subtotal = Decimal(str(original["total"]))

        descuento_esperado = (
            subtotal * Decimal("0.10")
        ).quantize(Decimal("0.01"))

        self.assertEqual(
            Decimal(resultado["subtotal_original"]),
            subtotal
        )

        self.assertEqual(
            Decimal(resultado["descuento"]),
            descuento_esperado
        )

        self.assertEqual(
            Decimal(resultado["total"]),
            subtotal - descuento_esperado
        )

        # Los tramos tarifarios no deben cambiar
        self.assertEqual(
            resultado["detalles"],
            original["detalles"]
        )

        # La promoción debe seguir disponible
        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )



    def test_95_confirmar_reserva_con_promocion(self):

        asignacion = self._asignacion_descuento()

        cotizacion = cotizar_reserva_con_promocion(
            self.cancha,
            self.inicio,
            self.fin,
            cliente=self.usuario,
            asignacion_id=asignacion.id
        )

        reserva = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin,
            asignacion_id=asignacion.id
        )

        asignacion.refresh_from_db()

        # La reserva tiene el precio final
        self.assertEqual(
            reserva.total,
            Decimal(cotizacion["total"])
        )

        self.assertEqual(
            reserva.estado,
            "CONFIRMADA"
        )

        # La promoción queda utilizada
        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        self.assertEqual(
            asignacion.reserva_utilizada,
            reserva
        )

        self.assertEqual(
            asignacion.descuento_aplicado,
            Decimal(cotizacion["descuento"])
        )

        self.assertIsNotNone(
            asignacion.fecha_uso
        )

        # Los detalles mantienen el precio original
        subtotal_detalles = sum(
            (
                detalle.subtotal
                for detalle in DetallePrecio.objects.filter(
                    reserva=reserva
                )
            ),
            Decimal("0.00")
        )

        self.assertEqual(
            subtotal_detalles,
            Decimal(cotizacion["subtotal_original"])
        )

        self.assertEqual(
            subtotal_detalles - asignacion.descuento_aplicado,
            reserva.total
        )



    def test_96_confirmar_sin_promocion(self):

        cotizacion = cotizar_reserva(
            self.cancha,
            self.inicio,
            self.fin
        )

        reserva = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        self.assertEqual(
            reserva.total,
            Decimal(str(cotizacion["total"]))
        )

        self.assertEqual(
            reserva.estado,
            "CONFIRMADA"
        )

        self.assertFalse(
            AsignacionPromocion.objects.filter(
                reserva_utilizada=reserva
            ).exists()
        )



    def test_97_no_confirmar_con_promocion_ajena(self):

        asignacion = self._asignacion_descuento()

        otro = get_user_model().objects.create_user(
            username="cliente_promo_ajena_97",
            email="promo97@example.com",
            password="ClaveSegura123!"
        )

        with self.assertRaises(DjangoPermissionDenied):

            confirmar_reserva_con_promocion(
                otro,
                self.cancha,
                self.inicio,
                self.fin,
                asignacion_id=asignacion.id
            )

        self.assertFalse(
            Reserva.objects.filter(cliente=otro).exists()
        )



    def test_98_revierte_reserva_si_promo_revocada(self):

        asignacion = self._asignacion_descuento()

        asignacion.estado = "REVOCADA"

        asignacion.full_clean()
        asignacion.save(update_fields=["estado"])

        with self.assertRaises(DjangoValidationError):

            confirmar_reserva_con_promocion(
                self.usuario,
                self.cancha,
                self.inicio,
                self.fin,
                asignacion_id=asignacion.id
            )

        # La transacción debe revertir la reserva
        self.assertFalse(
            Reserva.objects.filter(
                cliente=self.usuario
            ).exists()
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "REVOCADA"
        )

        self.assertIsNone(
            asignacion.reserva_utilizada
        )



    def test_99_no_confirmar_con_promo_vencida(self):

        asignacion = self._asignacion_descuento()

        promocion = asignacion.promocion

        promocion.fecha_fin = (
            timezone.now() - timedelta(minutes=1)
        )

        promocion.save(update_fields=["fecha_fin"])

        with self.assertRaises(DjangoValidationError):

            confirmar_reserva_con_promocion(
                self.usuario,
                self.cancha,
                self.inicio,
                self.fin,
                asignacion_id=asignacion.id
            )

        self.assertFalse(
            Reserva.objects.filter(
                cliente=self.usuario
            ).exists()
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )



    def test_100_confirmar_reserva_gratuita(self):

        asignacion = self._asignacion_descuento(
            tipo="PORCENTAJE",
            valor="100.00"
        )

        cotizacion = cotizar_reserva_con_promocion(
            self.cancha,
            self.inicio,
            self.fin,
            cliente=self.usuario,
            asignacion_id=asignacion.id
        )

        self.assertEqual(
            Decimal(cotizacion["total"]),
            Decimal("0.00")
        )

        reserva = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin,
            asignacion_id=asignacion.id
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            reserva.total,
            Decimal("0.00")
        )

        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        self.assertEqual(
            asignacion.descuento_aplicado,
            Decimal(cotizacion["subtotal_original"])
        )


    def test_101_api_cotizar_sin_promocion(self):

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.post(
            reverse("cotizar"),
            self.datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        original = cotizar_reserva(
            self.cancha,
            self.inicio,
            self.fin
        )

        self.assertEqual(
            Decimal(str(respuesta.data["total"])),
            Decimal(str(original["total"]))
        )


    def test_102_api_cotizar_con_promocion(self):

        asignacion = self._asignacion_descuento()

        self.api.force_authenticate(user=self.usuario)

        datos = {
            **self.datos,
            "asignacion_id": asignacion.id
        }

        respuesta = self.api.post(
            reverse("cotizar"),
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        subtotal = Decimal(
            respuesta.data["subtotal_original"]
        )

        descuento = Decimal(
            respuesta.data["descuento"]
        )

        total = Decimal(
            respuesta.data["total"]
        )

        self.assertEqual(
            subtotal - descuento,
            total
        )

        self.assertEqual(
            respuesta.data["promocion"]["asignacion_id"],
            asignacion.id
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )


    def test_103_api_confirmar_con_promocion(self):

        asignacion = self._asignacion_descuento()

        self.api.force_authenticate(user=self.usuario)

        datos = {
            **self.datos,
            "asignacion_id": asignacion.id
        }

        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        reserva = Reserva.objects.get(
            cliente=self.usuario,
            cancha=self.cancha
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            reserva.estado,
            "CONFIRMADA"
        )

        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        self.assertEqual(
            asignacion.reserva_utilizada,
            reserva
        )

        self.assertEqual(
            Decimal(str(respuesta.data["total"])),
            reserva.total
        )

        subtotal_original = sum(
            (
                detalle.subtotal
                for detalle in DetallePrecio.objects.filter(
                    reserva=reserva
                )
            ),
            Decimal("0.00")
        )

        self.assertEqual(
            reserva.total,
            subtotal_original - asignacion.descuento_aplicado
        )


    def test_104_api_confirmar_sin_promocion(self):

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            self.datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        reserva = Reserva.objects.get(
            cliente=self.usuario
        )

        self.assertEqual(
            reserva.estado,
            "CONFIRMADA"
        )

        self.assertFalse(
            AsignacionPromocion.objects.filter(
                reserva_utilizada=reserva
            ).exists()
        )


    def test_105_api_rechaza_promocion_ajena(self):

        asignacion = self._asignacion_descuento()

        otro = get_user_model().objects.create_user(
            username="cliente_api_105",
            email="cliente105@example.com",
            password="ClaveSegura123!"
        )

        self.api.force_authenticate(user=otro)

        datos = {
            **self.datos,
            "asignacion_id": asignacion.id
        }

        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            403,
            respuesta.data
        )

        self.assertFalse(
            Reserva.objects.filter(
                cliente=otro
            ).exists()
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "DISPONIBLE"
        )


    def test_106_api_rechaza_promocion_revocada(self):

        asignacion = self._asignacion_descuento()

        asignacion.estado = "REVOCADA"
        asignacion.full_clean()
        asignacion.save(update_fields=["estado"])

        self.api.force_authenticate(user=self.usuario)

        datos = {
            **self.datos,
            "asignacion_id": asignacion.id
        }

        respuesta = self.api.post(
            reverse("confirmar-reserva"),
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            400,
            respuesta.data
        )

        self.assertFalse(
            Reserva.objects.filter(
                cliente=self.usuario
            ).exists()
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "REVOCADA"
        )


    def test_107_api_rechaza_asignacion_invalida(self):

        self.api.force_authenticate(user=self.usuario)

        datos = {
            **self.datos,
            "asignacion_id": -1
        }

        respuesta_cotizacion = self.api.post(
            reverse("cotizar"),
            datos,
            format="json"
        )

        respuesta_confirmacion = self.api.post(
            reverse("confirmar-reserva"),
            datos,
            format="json"
        )

        self.assertEqual(
            respuesta_cotizacion.status_code,
            400
        )

        self.assertEqual(
            respuesta_confirmacion.status_code,
            400
        )

        self.assertFalse(
            Reserva.objects.filter(
                cliente=self.usuario
            ).exists()
        )



    def test_108_admin_modulos_recomendaciones(self):

        administrador = get_user_model().objects.create_superuser(
            username="admin_modulos_108",
            email="admin108@example.com",
            password="ClaveSegura123!"
        )

        self.client.force_login(administrador)

        modelos = (
            "recomendacion",
            "ejecucionregla",
            "promocion",
            "asignacionpromocion",
        )

        for modelo in modelos:

            url = reverse(
                f"admin:reservas_{modelo}_changelist"
            )

            respuesta = self.client.get(url)

            self.assertEqual(
                respuesta.status_code,
                200,
                modelo
            )



    def test_109_admin_crea_promocion(self):

        administrador = get_user_model().objects.create_superuser(
            username="admin_promo_109",
            email="admin109@example.com",
            password="ClaveSegura123!"
        )

        self.client.force_login(administrador)

        ahora = timezone.now()

        inicio = timezone.localtime(
            ahora - timedelta(days=1)
        )

        fin = timezone.localtime(
            ahora + timedelta(days=7)
        )

        datos = {
            "nombre": "Promoción desde Admin",
            "codigo": "ADMIN109",
            "descripcion": "Campaña de prueba.",
            "tipo_descuento": "PORCENTAJE",
            "valor_descuento": "10.00",
            "regla_objetivo": "R01",
            "fecha_inicio_0": inicio.strftime("%Y-%m-%d"),
            "fecha_inicio_1": inicio.strftime("%H:%M:%S"),
            "fecha_fin_0": fin.strftime("%Y-%m-%d"),
            "fecha_fin_1": fin.strftime("%H:%M:%S"),
            "limite_usos": "20",
            "activa": "on",
        }

        respuesta = self.client.post(
            reverse("admin:reservas_promocion_add"),
            datos
        )

        self.assertEqual(respuesta.status_code, 302)

        promocion = Promocion.objects.get(
            codigo="ADMIN109"
        )

        self.assertEqual(
            promocion.regla_objetivo,
            "R01"
        )

        self.assertEqual(
            promocion.valor_descuento,
            Decimal("10.00")
        )



    def test_110_admin_lista_promociones(self):

        promocion = self._promocion_ejemplo(
            codigo="LISTADO110"
        )

        promocion.full_clean()
        promocion.save()

        administrador = get_user_model().objects.create_superuser(
            username="admin_listado_110",
            email="admin110@example.com",
            password="ClaveSegura123!"
        )

        self.client.force_login(administrador)

        respuesta = self.client.get(
            reverse("admin:reservas_promocion_changelist")
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertContains(
            respuesta,
            "LISTADO110"
        )

        self.assertContains(
            respuesta,
            "0 / 50"
        )



    def test_111_admin_no_modifica_recomendacion(self):

        recomendacion = self._recomendacion_ejemplo()

        recomendacion.full_clean()
        recomendacion.save()

        administrador = get_user_model().objects.create_superuser(
            username="admin_auditoria_111",
            email="admin111@example.com",
            password="ClaveSegura123!"
        )

        self.client.force_login(administrador)

        url = reverse(
            "admin:reservas_recomendacion_change",
            args=[recomendacion.id]
        )

        # Debe poder consultarla
        consulta = self.client.get(url)

        self.assertEqual(consulta.status_code, 200)

        # No debe poder modificarla
        modificacion = self.client.post(
            url,
            {"titulo": "Modificación no autorizada"}
        )

        self.assertEqual(
            modificacion.status_code,
            403
        )

        recomendacion.refresh_from_db()

        self.assertEqual(
            recomendacion.titulo,
            "Opciones económicas"
        )



    def test_112_admin_no_crea_asignaciones(self):

        asignacion = self._asignacion_descuento()

        administrador = get_user_model().objects.create_superuser(
            username="admin_asignacion_112",
            email="admin112@example.com",
            password="ClaveSegura123!"
        )

        self.client.force_login(administrador)

        # Puede consultar la asignación
        detalle = self.client.get(
            reverse(
                "admin:reservas_asignacionpromocion_change",
                args=[asignacion.id]
            )
        )

        self.assertEqual(detalle.status_code, 200)

        # No puede crear asignaciones manualmente
        agregar = self.client.get(
            reverse("admin:reservas_asignacionpromocion_add")
        )

        self.assertEqual(agregar.status_code, 403)


    def test_113_api_recomendaciones_vacias(self):

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.get(
            reverse("mis-recomendaciones")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["cantidad"], 0)
        self.assertEqual(respuesta.data["recomendaciones"], [])


    def test_114_api_solo_mis_recomendaciones(self):

        mia = self._recomendacion_ejemplo()
        mia.full_clean()
        mia.save()

        otro = get_user_model().objects.create_user(
            username="otro_recomendaciones_114",
            email="otro114@example.com",
            password="ClaveSegura123!"
        )

        ajena = self._recomendacion_ejemplo(
            cliente=otro,
            titulo="Recomendación ajena"
        )
        ajena.full_clean()
        ajena.save()

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.get(
            reverse("mis-recomendaciones")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["cantidad"], 1)

        self.assertEqual(
            respuesta.data["recomendaciones"][0]["id"],
            mia.id
        )


    def test_115_api_excluye_recomendaciones_vencidas(self):

        vigente = self._recomendacion_ejemplo()
        vigente.full_clean()
        vigente.save()

        caducada = self._recomendacion_ejemplo(
            titulo="Recomendación caducada"
        )
        caducada.full_clean()
        caducada.save()

        # Simular el vencimiento después de crearla
        Recomendacion.objects.filter(
            pk=caducada.pk
        ).update(
            vence_en=timezone.now() - timedelta(days=1)
        )

        inactiva = self._recomendacion_ejemplo(
            titulo="Recomendación inactiva",
            activa=False
        )
        inactiva.full_clean()
        inactiva.save()

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.get(
            reverse("mis-recomendaciones")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["cantidad"], 1)

        self.assertEqual(
            respuesta.data["recomendaciones"][0]["id"],
            vigente.id
        )


    def test_116_api_promociones_disponibles(self):

        asignacion = self._asignacion_descuento()

        otro = get_user_model().objects.create_user(
            username="otro_promociones_116",
            email="otro116@example.com",
            password="ClaveSegura123!"
        )

        # Otro usuario recibe la misma campaña
        asignacion_ajena = AsignacionPromocion(
            cliente=otro,
            promocion=asignacion.promocion,
            motivo_asignacion="Campaña de prueba."
        )
        asignacion_ajena.full_clean()
        asignacion_ajena.save()

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta.data["cantidad_disponibles"],
            1
        )

        self.assertEqual(
            respuesta.data["cantidad_utilizadas"],
            0
        )

        self.assertEqual(
            respuesta.data["disponibles"][0]["id"],
            asignacion.id
        )


    def test_117_api_excluye_promociones_no_vigentes(self):

        asignacion = self._asignacion_descuento()
        promocion = asignacion.promocion

        self.api.force_authenticate(user=self.usuario)

        # Desactivar la campaña
        promocion.activa = False
        promocion.save(update_fields=["activa"])

        respuesta = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(
            respuesta.data["cantidad_disponibles"],
            0
        )

        # Reactivarla, pero simular una campaña vencida
        ahora = timezone.now()

        Promocion.objects.filter(
            pk=promocion.pk
        ).update(
            activa=True,
            fecha_inicio=ahora - timedelta(days=3),
            fecha_fin=ahora - timedelta(days=1)
        )

        respuesta = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(
            respuesta.data["cantidad_disponibles"],
            0
        )


    def test_118_api_historial_promociones_utilizadas(self):

        asignacion = self._asignacion_descuento()

        reserva = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin,
            asignacion_id=asignacion.id
        )

        self.api.force_authenticate(user=self.usuario)

        respuesta = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta.data["cantidad_disponibles"],
            0
        )

        self.assertEqual(
            respuesta.data["cantidad_utilizadas"],
            1
        )

        utilizada = respuesta.data["utilizadas"][0]

        self.assertEqual(
            utilizada["estado"],
            "UTILIZADA"
        )

        self.assertEqual(
            utilizada["reserva_utilizada"],
            reserva.id
        )

        self.assertGreater(
            Decimal(utilizada["descuento_aplicado"]),
            Decimal("0.00")
        )


    def test_119_api_actualiza_beneficios(self):

        # 1. Crear encuesta por cancelación de precio
        self._preparar_cancelacion_precio()

        # 2. Crear una campaña R01
        promocion = self._promocion_ejemplo(
            regla_objetivo="R01"
        )
        promocion.full_clean()
        promocion.save()

        self.api.force_authenticate(user=self.usuario)

        # 3. Antes de actualizar, no hay beneficios
        antes = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(
            antes.data["cantidad_disponibles"],
            0
        )

        # 4. Ejecutar el motor desde la API
        respuesta = self.api.post(
            reverse("actualizar-beneficios"),
            {},
            format="json"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["promociones_nuevas"],
            1
        )

        # 5. Consultar recomendaciones
        recomendaciones = self.api.get(
            reverse("mis-recomendaciones")
        )

        reglas = [
            item["regla"]
            for item in recomendaciones.data["recomendaciones"]
        ]

        self.assertIn("R01", reglas)

        # 6. Consultar promociones
        promociones = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(
            promociones.data["cantidad_disponibles"],
            1
        )

        self.assertEqual(
            promociones.data["disponibles"][0]["codigo"],
            promocion.codigo
        )

        # 7. Ejecutar nuevamente: no debe duplicar
        segunda = self.api.post(
            reverse("actualizar-beneficios"),
            {},
            format="json"
        )

        self.assertEqual(
            segunda.data["promociones_nuevas"],
            0
        )

        self.assertEqual(
            AsignacionPromocion.objects.filter(
                cliente=self.usuario,
                promocion=promocion
            ).count(),
            1
        )

        # Se registraron dos evaluaciones de 4 reglas
        self.assertEqual(
            EjecucionRegla.objects.filter(
                cliente=self.usuario
            ).count(),
            8
        )


    def test_120_api_beneficios_exigen_autenticacion(self):

        self.api.force_authenticate(user=None)

        urls = (
            reverse("mis-recomendaciones"),
            reverse("mis-promociones"),
        )

        for url in urls:

            respuesta = self.api.get(url)

            self.assertIn(
                respuesta.status_code,
                (401, 403)
            )

        respuesta = self.api.post(
            reverse("actualizar-beneficios"),
            {},
            format="json"
        )

        self.assertIn(
            respuesta.status_code,
            (401, 403)
        )


    def test_121_flujo_completo_personalizacion(self):

        # 1. Crear reserva, cancelarla y responder
        # la encuesta por precio
        reserva_inicial = self._preparar_cancelacion_precio()

        # 2. Crear campaña vinculada a R01
        promocion = self._promocion_ejemplo(
            regla_objetivo="R01"
        )

        promocion.full_clean()
        promocion.save()

        self.api.force_authenticate(user=self.usuario)

        # 3. Ejecutar el motor mediante la API
        actualizar = self.api.post(
            reverse("actualizar-beneficios"),
            {},
            format="json"
        )

        self.assertEqual(actualizar.status_code, 200)
        self.assertEqual(
            actualizar.data["promociones_nuevas"],
            1
        )

        # 4. Comprobar la recomendación R01
        respuesta_recomendaciones = self.api.get(
            reverse("mis-recomendaciones")
        )

        reglas = [
            item["regla"]
            for item in respuesta_recomendaciones.data[
                "recomendaciones"
            ]
        ]

        self.assertIn("R01", reglas)

        # 5. Consultar la promoción asignada
        promociones = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(
            promociones.data["cantidad_disponibles"],
            1
        )

        asignacion_id = promociones.data[
            "disponibles"
        ][0]["id"]

        # 6. Preparar nueva cotización
        datos = {
            **self.datos,
            "asignacion_id": asignacion_id
        }

        cotizacion = self.api.post(
            reverse("cotizar"),
            datos,
            format="json"
        )

        self.assertEqual(
            cotizacion.status_code,
            200,
            cotizacion.data
        )

        descuento = Decimal(
            str(cotizacion.data["descuento"])
        )

        subtotal = Decimal(
            str(cotizacion.data["subtotal_original"])
        )

        total = Decimal(
            str(cotizacion.data["total"])
        )

        self.assertGreater(
            descuento,
            Decimal("0.00")
        )

        self.assertEqual(
            subtotal - descuento,
            total
        )

        # 7. Confirmar con la promoción
        confirmacion = self.api.post(
            reverse("confirmar-reserva"),
            datos,
            format="json"
        )

        self.assertEqual(
            confirmacion.status_code,
            201,
            confirmacion.data
        )

        # 8. Consultar los datos guardados
        asignacion = AsignacionPromocion.objects.get(
            pk=asignacion_id
        )

        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        nueva_reserva = asignacion.reserva_utilizada

        self.assertIsNotNone(nueva_reserva)

        self.assertEqual(
            nueva_reserva.total,
            total
        )

        self.assertEqual(
            asignacion.descuento_aplicado,
            descuento
        )

        # 9. La reserva inicial sigue cancelada
        reserva_inicial.refresh_from_db()

        self.assertEqual(
            reserva_inicial.estado,
            "CANCELADA"
        )

        self.assertNotEqual(
            nueva_reserva.id,
            reserva_inicial.id
        )

        # 10. Verificar el historial de beneficios
        promociones_finales = self.api.get(
            reverse("mis-promociones")
        )

        self.assertEqual(
            promociones_finales.data[
                "cantidad_disponibles"
            ],
            0
        )

        self.assertEqual(
            promociones_finales.data[
                "cantidad_utilizadas"
            ],
            1
        )


    def test_122_cancelar_reserva_con_promocion(self):

        # 1. Crear promoción asignada
        asignacion = self._asignacion_descuento()

        # 2. Confirmar reserva con descuento
        reserva = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin,
            asignacion_id=asignacion.id
        )

        total_original_reserva = reserva.total

        asignacion.refresh_from_db()

        descuento_original = (
            asignacion.descuento_aplicado
        )

        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        # 3. Cancelar la reserva
        cancelar_reserva(
            reserva,
            self.usuario
        )

        reserva.refresh_from_db()
        asignacion.refresh_from_db()

        # 4. Verificar la cancelación
        self.assertEqual(
            reserva.estado,
            "CANCELADA"
        )

        # 5. La promoción permanece utilizada
        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        self.assertEqual(
            asignacion.reserva_utilizada_id,
            reserva.id
        )

        # 6. No se pierde el historial financiero
        self.assertEqual(
            asignacion.descuento_aplicado,
            descuento_original
        )

        self.assertEqual(
            reserva.total,
            total_original_reserva
        )

        # 7. Se genera la encuesta de cancelación
        self.assertTrue(
            Encuesta.objects.filter(
                reserva=reserva,
                tipo=Encuesta.TIPO_CANCELACION
            ).exists()
        )



    def test_123_no_reutiliza_promocion_tras_cancelar(self):

        asignacion = self._asignacion_descuento()

        # Primera reserva con descuento
        reserva = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin,
            asignacion_id=asignacion.id
        )

        # Cancelar la reserva
        cancelar_reserva(
            reserva,
            self.usuario
        )

        # Intentar reutilizar la promoción
        with self.assertRaises(DjangoValidationError):

            confirmar_reserva_con_promocion(
                self.usuario,
                self.cancha,
                self.inicio,
                self.fin,
                asignacion_id=asignacion.id
            )

        # No debe existir una segunda reserva
        self.assertEqual(
            Reserva.objects.filter(
                cliente=self.usuario
            ).count(),
            1
        )

        self.assertFalse(
            Reserva.objects.filter(
                cliente=self.usuario,
                estado="CONFIRMADA"
            ).exists()
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )



    def test_124_puede_reservar_sin_promo_tras_cancelar(self):

        asignacion = self._asignacion_descuento()

        # 1. Primera reserva con descuento
        primera = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin,
            asignacion_id=asignacion.id
        )

        # 2. Cancelar primera reserva
        cancelar_reserva(
            primera,
            self.usuario
        )

        # 3. Obtener cotización normal
        cotizacion = cotizar_reserva(
            self.cancha,
            self.inicio,
            self.fin
        )

        # 4. Confirmar sin promoción
        segunda = confirmar_reserva_con_promocion(
            self.usuario,
            self.cancha,
            self.inicio,
            self.fin
        )

        # 5. Verificar los resultados
        self.assertEqual(
            segunda.estado,
            "CONFIRMADA"
        )

        self.assertEqual(
            segunda.total,
            Decimal(str(cotizacion["total"]))
        )

        self.assertNotEqual(
            primera.id,
            segunda.id
        )

        # La promoción original sigue consumida
        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.estado,
            "UTILIZADA"
        )

        self.assertEqual(
            asignacion.reserva_utilizada_id,
            primera.id
        )
