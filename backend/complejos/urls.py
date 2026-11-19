from django.urls import path

from .views import (
    CanchaDetalleView,
    CanchaListadoView,
    ComplejoDetalleView,
    ComplejoListadoView,
)


app_name = "complejos"

urlpatterns = [
    path("complejos/", ComplejoListadoView.as_view(), name="complejo-listado"),
    path("complejos/<int:pk>/", ComplejoDetalleView.as_view(), name="complejo-detalle"),
    path("canchas/", CanchaListadoView.as_view(), name="cancha-listado"),
    path("canchas/<int:pk>/", CanchaDetalleView.as_view(), name="cancha-detalle"),
]
