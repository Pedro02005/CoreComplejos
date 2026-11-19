
from collections import Counter
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django.core.exceptions import (
    PermissionDenied,
    ValidationError
)
from django.db.models import Count
from django.utils import timezone

from reservas.models import Reserva, HistorialReserva


ZONA = ZoneInfo("America/Guayaquil")


def obtener_estadisticas_historial(cliente, dias=90):

    # 1. Validar al usuario
    if (
        not cliente.is_authenticated
        or not cliente.pk
    ):
        raise PermissionDenied(
            "Debes iniciar sesión."
        )

    if type(dias) is not int or not 1 <= dias <= 365:
        raise ValidationError(
            "El período debe estar entre 1 y 365 días."
        )

    ahora = timezone.now()
    fecha_inicio = ahora - timedelta(days=dias)

    # 2. Reservas confirmadas cuyo horario terminó
    reservas = Reserva.objects.filter(
        cliente=cliente,
        estado="CONFIRMADA",
        fin__gte=fecha_inicio,
        fin__lte=ahora
    )

    total_reservas = reservas.count()

    # 3. Contar cancelaciones realizadas recientemente
    cancelaciones = HistorialReserva.objects.filter(
        reserva__cliente=cliente,
        evento="CANCELACION",
        fecha__gte=fecha_inicio,
        fecha__lte=ahora
    ).count()

    # 4. Obtener deporte favorito
    deporte = (
        reservas.values(
            "cancha__deporte"
        ).annotate(
            cantidad=Count("id")
        ).order_by(
            "-cantidad",
            "cancha__deporte"
        ).first()
    )

    deporte_favorito = None

    if deporte:
        deporte_favorito = {
            "codigo": deporte["cancha__deporte"],
            "cantidad": deporte["cantidad"]
        }

    # 5. Obtener complejo favorito
    complejo = (
        reservas.values(
            "cancha__complejo_id",
            "cancha__complejo__nombre"
        ).annotate(
            cantidad=Count("id")
        ).order_by(
            "-cantidad",
            "cancha__complejo_id"
        ).first()
    )

    complejo_favorito = None

    if complejo:
        complejo_favorito = {
            "id": complejo["cancha__complejo_id"],
            "nombre": complejo["cancha__complejo__nombre"],
            "cantidad": complejo["cantidad"]
        }

    # 6. Analizar franjas horarias y precios
    franjas = Counter()

    importe_total = Decimal("0.00")
    minutos_totales = Decimal("0")

    for reserva in reservas:

        inicio_local = timezone.localtime(
            reserva.inicio,
            ZONA
        )

        hora = inicio_local.hour

        if hora < 12:
            franja = "MANANA"

        elif hora < 18:
            franja = "TARDE"

        else:
            franja = "NOCHE"

        franjas[franja] += 1

        importe_total += reserva.total

        minutos = Decimal(
            str(
                (reserva.fin - reserva.inicio)
                .total_seconds()
            )
        ) / Decimal("60")

        minutos_totales += minutos

    # 7. Determinar franja preferida
    franja_preferida = None

    if franjas:

        codigo, cantidad = sorted(
            franjas.items(),
            key=lambda item: (-item[1], item[0])
        )[0]

        franja_preferida = {
            "codigo": codigo,
            "cantidad": cantidad
        }

    # 8. Calcular precio por hora de referencia
    precio_referencia = None

    if minutos_totales > 0:

        precio = (
            importe_total
            * Decimal("60")
            / minutos_totales
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        precio_referencia = str(precio)

    # 9. Devolver estadísticas
    return {
        "periodo_dias": dias,

        "reservas_finalizadas": total_reservas,

        "cancelaciones_recientes": cancelaciones,

        "deporte_favorito": deporte_favorito,

        "complejo_favorito": complejo_favorito,

        "franja_preferida": franja_preferida,

        "precio_hora_referencia": precio_referencia,

        "muestra_suficiente": total_reservas >= 3
    }
