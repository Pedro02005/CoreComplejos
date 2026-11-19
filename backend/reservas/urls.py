
from django.urls import path

from .views import (
    DisponibilidadView,
    CotizarView,
    ConfirmarReservaView,
    CancelarReservaView,
    ReservaDetalleView,
    EncuestasPendientesView,
    ResponderEncuestaView
)


from .views import (
    MisRecomendacionesView,
    MisPromocionesView,
    ActualizarBeneficiosView
)


urlpatterns = [

    # Consultar disponibilidad
    path(
        "canchas/<int:cancha_id>/disponibilidad/",
        DisponibilidadView.as_view(),
        name="disponibilidad"
    ),

    # Cotizar una reserva
    path(
        "reservas/cotizar/",
        CotizarView.as_view(),
        name="cotizar"
    ),

    # Confirmar una reserva
    path(
        "reservas/",
        ConfirmarReservaView.as_view(),
        name="confirmar-reserva"
    ),

    # Cancelar una reserva existente
    path(
        "reservas/<int:reserva_id>/cancelar/",
        CancelarReservaView.as_view(),
        name="cancelar-reserva"
    ),
    
    
    path(
        "reservas/<int:reserva_id>/",
        ReservaDetalleView.as_view(),
        name="detalle-reserva"
    ),

    
    path(
        "encuestas/pendientes/",
        EncuestasPendientesView.as_view(),
        name="encuestas-pendientes"
    ),


    path(
        "encuestas/<int:encuesta_id>/responder/",
        ResponderEncuestaView.as_view(),
        name="responder-encuesta"
    ),

    path(
        "recomendaciones/",
        MisRecomendacionesView.as_view(),
        name="mis-recomendaciones"
    ),

    path(
        "recomendaciones/actualizar/",
        ActualizarBeneficiosView.as_view(),
        name="actualizar-beneficios"
    ),

    path(
        "promociones/mis-promociones/",
        MisPromocionesView.as_view(),
        name="mis-promociones"
    ),


]











