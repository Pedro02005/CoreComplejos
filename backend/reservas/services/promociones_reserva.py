
from decimal import Decimal

from django.core.exceptions import (
    ValidationError,
    PermissionDenied
)
from django.db import transaction
from django.utils import timezone

from reservas.models import AsignacionPromocion

from .cotizacion import cotizar_reserva
from .reserva import confirmar_reserva
from .descuentos import calcular_descuento


def obtener_asignacion_cliente(asignacion_id, cliente):

    # Validar autenticación
    if (
        cliente is None
        or not cliente.is_authenticated
        or not cliente.pk
    ):
        raise PermissionDenied(
            "Debes iniciar sesión."
        )

    # Validar identificador
    if (
        type(asignacion_id) is not int
        or asignacion_id <= 0
    ):
        raise ValidationError(
            "El identificador de promoción es inválido."
        )

    # Buscar la asignación
    asignacion = (
        AsignacionPromocion.objects
        .select_related("promocion")
        .filter(pk=asignacion_id)
        .first()
    )

    if asignacion is None:
        raise ValidationError(
            "La promoción asignada no existe."
        )

    # Verificar propiedad
    if asignacion.cliente_id != cliente.pk:
        raise PermissionDenied(
            "Esta promoción no te pertenece."
        )

    return asignacion


def cotizar_reserva_con_promocion(
    cancha,
    inicio,
    fin,
    cliente=None,
    asignacion_id=None
):

    # 1. Ejecutar la cotización original
    cotizacion = cotizar_reserva(
        cancha,
        inicio,
        fin
    )

    # 2. Si no existe promoción, no cambiar nada
    if asignacion_id is None:
        return cotizacion

    # 3. Verificar asignación y propietario
    asignacion = obtener_asignacion_cliente(
        asignacion_id,
        cliente
    )

    # 4. Calcular descuento sobre subtotal real
    descuento = calcular_descuento(
        asignacion,
        cliente,
        Decimal(str(cotizacion["total"]))
    )

    # 5. Construir respuesta con promoción
    resultado = dict(cotizacion)

    resultado.update({
        "subtotal_original": descuento["subtotal"],
        "descuento": descuento["descuento"],
        "total": descuento["total"],

        "promocion": {
            "asignacion_id": asignacion.id,
            "codigo": descuento["codigo_promocion"],
            "tipo_descuento": descuento["tipo_descuento"],
            "valor_descuento": descuento["valor_descuento"]
        }
    })

    return resultado


@transaction.atomic
def confirmar_reserva_con_promocion(
    cliente,
    cancha,
    inicio,
    fin,
    asignacion_id=None
):

    # 1. Mantener la confirmación normal
    if asignacion_id is None:
        return confirmar_reserva(
            cliente,
            cancha,
            inicio,
            fin
        )

    # 2. Verificar que la promoción pertenezca
    # al cliente antes de crear la reserva
    asignacion = obtener_asignacion_cliente(
        asignacion_id,
        cliente
    )

    # 3. Confirmar utilizando el servicio original.
    # Este vuelve a validar horarios, precios,
    # disponibilidad, solapamientos, etc.
    reserva = confirmar_reserva(
        cliente,
        cancha,
        inicio,
        fin
    )

    # 4. Obtener el subtotal confirmado real
    subtotal_original = Decimal(
        str(reserva.total)
    )

    # 5. Volver a comprobar la promoción usando
    # el precio de la reserva recién confirmada
    descuento = calcular_descuento(
        asignacion,
        cliente,
        subtotal_original
    )

    # 6. Actualizar solamente el total final
    reserva.total = Decimal(
        descuento["total"]
    )

    reserva.save(
        update_fields=["total"]
    )

    # 7. Registrar el uso de la promoción
    asignacion.refresh_from_db()

    asignacion.estado = "UTILIZADA"
    asignacion.fecha_uso = timezone.now()
    asignacion.reserva_utilizada = reserva

    asignacion.descuento_aplicado = Decimal(
        descuento["descuento"]
    )

    # 8. Validar y guardar la asignación
    asignacion.full_clean()

    asignacion.save(
        update_fields=[
            "estado",
            "fecha_uso",
            "reserva_utilizada",
            "descuento_aplicado"
        ]
    )

    # 9. Devolver el mismo tipo que el servicio original
    return reserva
