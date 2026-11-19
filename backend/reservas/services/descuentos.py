
from decimal import (
    Decimal,
    ROUND_HALF_UP,
    InvalidOperation
)

from django.core.exceptions import (
    ValidationError,
    PermissionDenied
)

from django.utils import timezone

from reservas.models import AsignacionPromocion


CENTAVOS = Decimal("0.01")


def calcular_descuento(asignacion, cliente, subtotal):

    # 1. Verificar autenticación
    if not cliente.is_authenticated or not cliente.pk:
        raise PermissionDenied(
            "Debes iniciar sesión."
        )

    # 2. Verificar que la asignación exista
    if not asignacion or not asignacion.pk:
        raise ValidationError(
            "La asignación debe estar guardada."
        )

    # 3. Obtener la asignación desde PostgreSQL
    asignacion = (
        AsignacionPromocion.objects
        .select_related("promocion")
        .filter(
            pk=asignacion.pk,
            cliente=cliente
        )
        .first()
    )

    if asignacion is None:
        raise PermissionDenied(
            "Esta promoción no te pertenece."
        )

    # 4. Verificar que no haya sido utilizada
    if asignacion.estado != "DISPONIBLE":
        raise ValidationError(
            "La promoción ya no está disponible."
        )

    promocion = asignacion.promocion
    ahora = timezone.now()

    # 5. Comprobar que la campaña esté activa
    if not promocion.activa:
        raise ValidationError(
            "La promoción está inactiva."
        )

    # 6. Validar las fechas de la campaña
    if (
        ahora < promocion.fecha_inicio
        or ahora >= promocion.fecha_fin
    ):
        raise ValidationError(
            "La promoción no está vigente."
        )

    # 7. Verificar el límite global de usos
    if promocion.limite_usos is not None:

        usos = AsignacionPromocion.objects.filter(
            promocion=promocion,
            estado="UTILIZADA"
        ).count()

        if usos >= promocion.limite_usos:
            raise ValidationError(
                "La promoción alcanzó su límite de usos."
            )

    # 8. Validar el subtotal recibido
    if isinstance(subtotal, (bool, float)):
        raise ValidationError(
            "El subtotal debe utilizar Decimal o texto decimal."
        )

    try:
        subtotal = Decimal(str(subtotal))

        if not subtotal.is_finite():
            raise ValidationError(
                "El subtotal debe ser un número finito."
            )

        if subtotal <= 0:
            raise ValidationError(
                "El subtotal debe ser mayor que cero."
            )

        if subtotal != subtotal.quantize(CENTAVOS):
            raise ValidationError(
                "El subtotal no puede tener fracciones de centavo."
            )

    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(
            "El subtotal no es un importe válido."
        )

    # 9. Calcular el descuento
    valor = promocion.valor_descuento

    if promocion.tipo_descuento == "PORCENTAJE":

        if not Decimal("0") < valor <= Decimal("100"):
            raise ValidationError(
                "El porcentaje configurado es inválido."
            )

        descuento = (
            subtotal * valor / Decimal("100")
        )

    elif promocion.tipo_descuento == "MONTO_FIJO":

        if valor <= 0:
            raise ValidationError(
                "El descuento fijo debe ser positivo."
            )

        descuento = valor

    else:
        raise ValidationError(
            "Tipo de descuento no reconocido."
        )

    # 10. Redondear a centavos
    descuento = descuento.quantize(
        CENTAVOS,
        rounding=ROUND_HALF_UP
    )

    # 11. Evitar descontar más que el subtotal
    descuento = min(descuento, subtotal)

    if descuento <= 0:
        raise ValidationError(
            "La promoción no genera un descuento aplicable."
        )

    # 12. Calcular total final
    total_final = subtotal - descuento

    # 13. Devolver el resultado
    return {
        "asignacion_id": asignacion.id,
        "promocion_id": promocion.id,
        "codigo_promocion": promocion.codigo,
        "tipo_descuento": promocion.tipo_descuento,
        "valor_descuento": str(valor),
        "subtotal": str(subtotal),
        "descuento": str(descuento),
        "total": str(total_final),
        "moneda": "USD"
    }
