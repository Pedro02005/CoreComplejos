from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from .models import Cancha, Complejo, Tarifa
from .serializers import (
    CanchaDetalleSerializer,
    CanchaListadoSerializer,
    ComplejoDetalleSerializer,
    ComplejoListadoSerializer,
    FiltrosCanchaSerializer,
    FiltrosComplejoSerializer,
)


class CatalogoPagination(PageNumberPagination):
    page_size = 20


class ComplejoListadoView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ComplejoListadoSerializer
    pagination_class = CatalogoPagination

    def get_queryset(self):
        filtros = FiltrosComplejoSerializer(data=self.request.query_params)
        filtros.is_valid(raise_exception=True)
        datos = filtros.validated_data

        complejos = Complejo.objects.filter(activo=True)
        if "ciudad" in datos:
            complejos = complejos.filter(ciudad__iexact=datos["ciudad"])
        if "nombre" in datos:
            complejos = complejos.filter(nombre__icontains=datos["nombre"])
        return complejos.order_by("nombre", "id")


class ComplejoDetalleView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ComplejoDetalleSerializer
    queryset = Complejo.objects.filter(activo=True).prefetch_related(
        Prefetch(
            "canchas",
            queryset=Cancha.objects.filter(activa=True)
            .select_related("complejo").order_by("nombre", "id"),
            to_attr="canchas_activas",
        )
    )


class CanchaListadoView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CanchaListadoSerializer
    pagination_class = CatalogoPagination

    def get_queryset(self):
        filtros = FiltrosCanchaSerializer(data=self.request.query_params)
        filtros.is_valid(raise_exception=True)
        datos = filtros.validated_data

        canchas = Cancha.objects.filter(
            activa=True, complejo__activo=True,
        ).select_related("complejo")
        if "complejo_id" in datos:
            canchas = canchas.filter(complejo_id=datos["complejo_id"])
        if "deporte" in datos:
            canchas = canchas.filter(deporte=datos["deporte"])
        if "ciudad" in datos:
            canchas = canchas.filter(complejo__ciudad__iexact=datos["ciudad"])
        if "nombre" in datos:
            canchas = canchas.filter(nombre__icontains=datos["nombre"])
        return canchas.order_by("nombre", "id")


class CanchaDetalleView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CanchaDetalleSerializer
    queryset = Cancha.objects.filter(
        activa=True, complejo__activo=True,
    ).select_related("complejo").prefetch_related(
        "horarios",
        Prefetch(
            "tarifas",
            queryset=Tarifa.objects.filter(activa=True),
            to_attr="tarifas_activas",
        ),
    )
