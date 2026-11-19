
from datetime import timedelta

from django.core.exceptions import (
    PermissionDenied,
    ValidationError
)
from django.db.models import Avg, Count
from django.utils import timezone

from reservas.models import (
    Encuesta,
    RespuestaEncuesta
)


def obtener_estadisticas_encuestas(cliente, dias=90):

    # 1. Validar al cliente
    if (
        not cliente.is_authenticated
        or not cliente.pk
    ):
        raise PermissionDenied(
            "Debes iniciar sesión para consultar estadísticas."
        )

    # 2. Validar el período de análisis
    if not isinstance(dias, int) or not 1 <= dias <= 365:
        raise ValidationError(
            "El período debe estar entre 1 y 365 días."
        )

    ahora = timezone.now()
    fecha_inicio = ahora - timedelta(days=dias)

    # 3. Obtener respuestas recientes del cliente
    respuestas = RespuestaEncuesta.objects.filter(
        encuesta__reserva__cliente=cliente,
        fecha_respuesta__gte=fecha_inicio,
        fecha_respuesta__lte=ahora
    )

    # 4. Separar respuestas por tipo
    cancelaciones = respuestas.filter(
        encuesta__tipo=Encuesta.TIPO_CANCELACION
    )

    experiencias = respuestas.filter(
        encuesta__tipo=Encuesta.TIPO_EXPERIENCIA
    )

    # 5. Contar los motivos de cancelación
    motivos = list(
        cancelaciones.values(
            "motivo_cancelacion"
        ).annotate(
            cantidad=Count("id")
        ).order_by(
            "-cantidad",
            "motivo_cancelacion"
        )
    )

    # 6. Obtener última respuesta de cancelación
    ultima_cancelacion = cancelaciones.order_by(
        "-fecha_respuesta", "-id"
    ).values(
        "motivo_cancelacion",
        "hubiera_evitado"
    ).first()

    # 7. Calcular satisfacción promedio
    resultado_promedio = experiencias.aggregate(
        promedio=Avg("calificacion")
    )

    promedio = resultado_promedio["promedio"]

    # 8. Contar respuestas de experiencia
    total_experiencias = experiencias.count()

    volveria_reservar = experiencias.filter(
        volveria_reservar=True
    ).count()

    # 9. Obtener última experiencia
    ultima_experiencia = experiencias.order_by(
        "-fecha_respuesta", "-id"
    ).values(
        "calificacion",
        "volveria_reservar",
        "aspecto_mejorar"
    ).first()

    # 10. Devolver estadísticas organizadas
    return {
        "periodo_dias": dias,

        "cancelaciones": {
            "cantidad_respuestas": cancelaciones.count(),
            "motivos": motivos,
            "ultima_respuesta": ultima_cancelacion
        },

        "experiencias": {
            "cantidad_respuestas": total_experiencias,

            "calificacion_promedio": (
                round(float(promedio), 2)
                if promedio is not None
                else None
            ),

            "volveria_reservar_si": volveria_reservar,

            "muestra_suficiente": (
                total_experiencias >= 3
            ),

            "ultima_respuesta": ultima_experiencia
        }
    }
