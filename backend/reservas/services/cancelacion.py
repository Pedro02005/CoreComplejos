
from django.db import transaction
from django.utils import timezone

from django.core.exceptions import (
    ValidationError,
    PermissionDenied
)

from reservas.models import HistorialReserva


from .encuestas import generar_encuesta_cancelacion


@transaction.atomic
def cancelar_reserva(reserva, actor, motivo=""):

    # 1. Verificar que el usuario esté autenticado
    if not actor.is_authenticated:
        raise PermissionDenied(
            "Debes iniciar sesión para cancelar."
        )

    # 2. Identificar si es un administrador
    es_admin = actor.is_superuser

    # 3. Verificar que el cliente sea dueño de la reserva
    if not es_admin and reserva.cliente_id != actor.pk:
        raise PermissionDenied(
            "No puedes cancelar reservas de otros usuarios."
        )

    # 4. Verificar el estado de la reserva
    if reserva.estado != "CONFIRMADA":
        raise ValidationError(
            "Solo se pueden cancelar reservas confirmadas."
        )

    # 5. Obtener la fecha y hora actual
    ahora = timezone.now()
    motivo = (motivo or "").strip()

    # 6. Validar los plazos de cancelación
    if es_admin:

        if ahora >= reserva.inicio:
            raise ValidationError(
                "No puedes cancelar una reserva que ya comenzó."
            )

        if not motivo:
            raise ValidationError(
                "El administrador debe indicar un motivo."
            )

    else:

        if ahora > reserva.cancelable_hasta:
            raise ValidationError(
                "El plazo de cancelación terminó. "
                "Debes cancelar al menos 12 horas antes."
            )

    # 7. Cambiar el estado de la reserva
    estado_anterior = reserva.estado

    reserva.estado = "CANCELADA"
    reserva.full_clean()
    reserva.save(update_fields=["estado"])

    # 8. Registrar el evento en el historial
    historial = HistorialReserva(
        reserva=reserva,
        actor=actor,
        evento="CANCELACION",
        estado_anterior=estado_anterior,
        estado_nuevo="CANCELADA",
        motivo=motivo
    )

    historial.full_clean()
    historial.save()
    
        # Generar automáticamente la encuesta
    generar_encuesta_cancelacion(reserva)

    # 9. Devolver la reserva actualizada
    return reserva
