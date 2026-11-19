
from uuid import uuid4
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction

from reservas.models import (
    Reserva,
    DetallePrecio,
    HistorialReserva
)

from .cotizacion import cotizar_reserva


@transaction.atomic
def confirmar_reserva(cliente, cancha, inicio, fin):

    # 1. Verificar disponibilidad y calcular el precio
    cotizacion = cotizar_reserva(
        cancha,
        inicio,
        fin
    )

    # 2. Crear la reserva
    reserva = Reserva(
        cliente=cliente,
        cancha=cancha,
        inicio=inicio,
        fin=fin,
        estado="CONFIRMADA",
        total=Decimal(cotizacion["total"]),
        clave_solicitud=uuid4(),
        cancelable_hasta=inicio - timedelta(hours=12)
    )

    reserva.full_clean()
    reserva.save()

    # 3. Guardar el detalle de cada tarifa aplicada
    for tramo in cotizacion["detalles"]:

        detalle = DetallePrecio(
            reserva=reserva,
            tarifa_id=tramo["tarifa_id"],
            inicio=datetime.fromisoformat(tramo["inicio"]),
            fin=datetime.fromisoformat(tramo["fin"]),
            valor_hora=Decimal(tramo["valor_hora"]),
            subtotal=Decimal(tramo["subtotal"])
        )

        detalle.full_clean()
        detalle.save()

    # 4. Registrar el evento en el historial
    historial = HistorialReserva(
        reserva=reserva,
        actor=cliente,
        evento="CREACION",
        estado_anterior="",
        estado_nuevo="CONFIRMADA",
        motivo=""
    )

    historial.full_clean()
    historial.save()

    # 5. Devolver la reserva confirmada
    return reserva
