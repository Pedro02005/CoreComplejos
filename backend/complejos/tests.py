from datetime import time
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Cancha, Complejo, HorarioAtencion, Tarifa


class CatalogoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quito = Complejo.objects.create(
            nombre="Centro Norte", ciudad="Quito", direccion="Av. Norte",
            descripcion="Complejo deportivo de Quito",
        )
        cls.cuenca = Complejo.objects.create(
            nombre="Centro Sur", ciudad="Cuenca", direccion="Av. Sur",
        )
        cls.inactivo = Complejo.objects.create(
            nombre="Centro cerrado", ciudad="Quito", direccion="Av. Central",
            activo=False,
        )
        cls.futbol = Cancha.objects.create(
            complejo=cls.quito, nombre="Cancha A", deporte="FUTBOL", capacidad=10,
        )
        cls.tenis = Cancha.objects.create(
            complejo=cls.quito, nombre="Cancha B", deporte="TENIS", capacidad=4,
        )
        cls.futbol_cuenca = Cancha.objects.create(
            complejo=cls.cuenca, nombre="Cancha C", deporte="FUTBOL", capacidad=10,
        )
        cls.cancha_inactiva = Cancha.objects.create(
            complejo=cls.quito, nombre="Cancha D", deporte="FUTBOL",
            capacidad=10, activa=False,
        )
        cls.cancha_complejo_inactivo = Cancha.objects.create(
            complejo=cls.inactivo, nombre="Cancha E", deporte="FUTBOL", capacidad=10,
        )
        cls.horario = HorarioAtencion.objects.create(
            cancha=cls.futbol, dia_semana=0, apertura=time(8), cierre=time(20),
        )
        cls.tarifa = Tarifa.objects.create(
            cancha=cls.futbol, dia_semana=0, inicio=time(8), fin=time(20),
            valor_hora=Decimal("25.50"),
        )
        Tarifa.objects.create(
            cancha=cls.futbol, dia_semana=0, inicio=time(8), fin=time(20),
            valor_hora=Decimal("10.00"), activa=False,
        )
        Tarifa.objects.create(
            cancha=cls.tenis, dia_semana=0, inicio=time(8), fin=time(20),
            valor_hora=Decimal("15.00"),
        )

    def test_complejos_publicos_excluyen_inactivos(self):
        respuesta = self.client.get(reverse("complejos:complejo-listado"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 2)
        self.assertEqual(
            [item["id"] for item in respuesta.data["results"]],
            [self.quito.pk, self.cuenca.pk],
        )
        self.assertEqual(respuesta.data["results"][0]["direccion"], "Av. Norte")

    def test_filtros_complejos_se_combinan_y_no_distinguen_mayusculas(self):
        respuesta = self.client.get(
            reverse("complejos:complejo-listado"),
            {"ciudad": " quito ", "nombre": "NORTE"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(respuesta.data["results"][0]["id"], self.quito.pk)
        respuesta = self.client.get(
            reverse("complejos:complejo-listado"),
            {"ciudad": "Quito", "nombre": "Sur"},
        )
        self.assertEqual(respuesta.data["results"], [])

    def test_detalle_complejo_incluye_solo_sus_canchas_activas(self):
        respuesta = self.client.get(
            reverse("complejos:complejo-detalle", args=[self.quito.pk]),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["descripcion"], self.quito.descripcion)
        self.assertEqual(
            [item["id"] for item in respuesta.data["canchas"]],
            [self.futbol.pk, self.tenis.pk],
        )

    def test_detalle_complejo_sin_canchas_devuelve_lista_vacia(self):
        complejo = Complejo.objects.create(
            nombre="Nuevo", ciudad="Quito", direccion="Av. Nueva",
        )
        respuesta = self.client.get(
            reverse("complejos:complejo-detalle", args=[complejo.pk]),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["canchas"], [])

    def test_complejo_inactivo_o_inexistente_devuelve_404(self):
        for identificador in (self.inactivo.pk, 999999):
            with self.subTest(identificador=identificador):
                respuesta = self.client.get(
                    reverse("complejos:complejo-detalle", args=[identificador]),
                )
                self.assertEqual(respuesta.status_code, 404)

    def test_canchas_publicas_excluyen_canchas_y_complejos_inactivos(self):
        respuesta = self.client.get(reverse("complejos:cancha-listado"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 3)
        self.assertEqual(
            [item["id"] for item in respuesta.data["results"]],
            [self.futbol.pk, self.tenis.pk, self.futbol_cuenca.pk],
        )
        cancha = respuesta.data["results"][0]
        self.assertEqual(cancha["complejo"], self.quito.pk)
        self.assertEqual(cancha["complejo_nombre"], self.quito.nombre)
        self.assertEqual(cancha["ciudad"], "Quito")

    def test_filtros_canchas_individuales_y_combinados(self):
        casos = (
            ({"complejo_id": self.quito.pk}, [self.futbol.pk, self.tenis.pk]),
            ({"deporte": "FUTBOL"}, [self.futbol.pk, self.futbol_cuenca.pk]),
            ({"ciudad": "cuenca"}, [self.futbol_cuenca.pk]),
            ({"nombre": "cancha b"}, [self.tenis.pk]),
            ({"complejo_id": self.quito.pk, "deporte": "TENIS", "ciudad": "QUITO"}, [self.tenis.pk]),
            ({"complejo_id": self.quito.pk, "ciudad": "Cuenca"}, []),
            ({"complejo_id": self.inactivo.pk}, []),
            ({"complejo_id": 999999}, []),
        )
        for filtros, esperados in casos:
            with self.subTest(filtros=filtros):
                respuesta = self.client.get(reverse("complejos:cancha-listado"), filtros)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(
                    [item["id"] for item in respuesta.data["results"]], esperados,
                )

    def test_filtros_invalidos_devuelven_400(self):
        for filtros in (
            {"complejo_id": "abc"}, {"complejo_id": 0}, {"complejo_id": -1},
            {"deporte": "AJEDREZ"}, {"ciudad": " "},
        ):
            with self.subTest(filtros=filtros):
                respuesta = self.client.get(reverse("complejos:cancha-listado"), filtros)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(next(iter(filtros)), respuesta.data)
        respuesta = self.client.get(
            reverse("complejos:complejo-listado"), {"ciudad": " "},
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_detalle_cancha_incluye_horarios_y_solo_tarifas_propias_activas(self):
        respuesta = self.client.get(
            reverse("complejos:cancha-detalle", args=[self.futbol.pk]),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["complejo"], self.quito.pk)
        self.assertEqual(respuesta.data["capacidad"], 10)
        self.assertEqual(len(respuesta.data["horarios"]), 1)
        self.assertEqual(respuesta.data["horarios"][0]["id"], self.horario.pk)
        self.assertEqual(respuesta.data["horarios"][0]["apertura"], "08:00:00")
        self.assertEqual(len(respuesta.data["tarifas"]), 1)
        self.assertEqual(respuesta.data["tarifas"][0]["id"], self.tarifa.pk)
        self.assertEqual(respuesta.data["tarifas"][0]["valor_hora"], "25.50")

    def test_detalle_cancha_sin_configuracion_devuelve_listas_vacias(self):
        respuesta = self.client.get(
            reverse("complejos:cancha-detalle", args=[self.futbol_cuenca.pk]),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["horarios"], [])
        self.assertEqual(respuesta.data["tarifas"], [])

    def test_cancha_inactiva_de_complejo_inactivo_o_inexistente_devuelve_404(self):
        for identificador in (
            self.cancha_inactiva.pk, self.cancha_complejo_inactivo.pk, 999999,
        ):
            with self.subTest(identificador=identificador):
                respuesta = self.client.get(
                    reverse("complejos:cancha-detalle", args=[identificador]),
                )
                self.assertEqual(respuesta.status_code, 404)

    def test_paginacion_complejos_conserva_filtro_y_orden(self):
        Complejo.objects.bulk_create([
            Complejo(nombre=f"Nuevo {numero:02d}", ciudad="Loja", direccion="Av. Loja")
            for numero in range(21)
        ])
        url = reverse("complejos:complejo-listado")
        primera = self.client.get(url, {"ciudad": "Loja"})
        self.assertEqual(primera.status_code, 200)
        self.assertEqual(primera.data["count"], 21)
        self.assertEqual(len(primera.data["results"]), 20)
        self.assertIsNone(primera.data["previous"])
        self.assertIn("ciudad=Loja", primera.data["next"])
        segunda = self.client.get(primera.data["next"])
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual([item["nombre"] for item in segunda.data["results"]], ["Nuevo 20"])
        self.assertIsNone(segunda.data["next"])

    def test_paginacion_canchas_no_repite_resultados(self):
        Cancha.objects.bulk_create([
            Cancha(complejo=self.quito, nombre=f"Nueva {numero:02d}", deporte="PADEL", capacidad=4)
            for numero in range(21)
        ])
        primera = self.client.get(reverse("complejos:cancha-listado"), {"deporte": "PADEL"})
        self.assertEqual(primera.status_code, 200)
        self.assertEqual(primera.data["count"], 21)
        self.assertEqual(len(primera.data["results"]), 20)
        segunda = self.client.get(primera.data["next"])
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(len(segunda.data["results"]), 1)
        self.assertTrue(
            {item["id"] for item in primera.data["results"]}.isdisjoint(
                item["id"] for item in segunda.data["results"]
            )
        )

    def test_pagina_inexistente_devuelve_404(self):
        for nombre in ("complejos:complejo-listado", "complejos:cancha-listado"):
            with self.subTest(nombre=nombre):
                respuesta = self.client.get(reverse(nombre), {"page": 999})
                self.assertEqual(respuesta.status_code, 404)

    def test_catalogo_rechaza_escrituras(self):
        urls = (
            reverse("complejos:complejo-listado"),
            reverse("complejos:complejo-detalle", args=[self.quito.pk]),
            reverse("complejos:cancha-listado"),
            reverse("complejos:cancha-detalle", args=[self.futbol.pk]),
        )
        for url in urls:
            for metodo in ("post", "put", "patch", "delete"):
                with self.subTest(url=url, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(url, {"nombre": "Cambio"}, format="json")
                    self.assertEqual(respuesta.status_code, 405)
        self.quito.refresh_from_db()
        self.futbol.refresh_from_db()
        self.assertEqual(self.quito.nombre, "Centro Norte")
        self.assertEqual(self.futbol.nombre, "Cancha A")
        self.assertEqual(Complejo.objects.count(), 3)
        self.assertEqual(Cancha.objects.count(), 5)

    def test_ruta_disponibilidad_existente_sigue_accesible(self):
        respuesta = self.client.get(
            reverse("disponibilidad", kwargs={"cancha_id": self.futbol.pk}),
            {"fecha": "2000-01-03", "duracion": 60},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["opciones"], [])
