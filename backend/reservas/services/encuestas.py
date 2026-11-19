
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

from django.db import transaction
from reservas.models import Encuesta, Reserva, RespuestaEncuesta



def generar_encuesta_cancelacion(reserva):

    # 1. Verificar que la reserva exista en la BD
    if not reserva.pk:
        raise ValidationError(
            "La reserva debe estar guardada."
        )

    # 2. Obtener el estado actualizado
    reserva.refresh_from_db(fields=["estado"])

    # 3. Validar que esté cancelada
    if reserva.estado != "CANCELADA":
        raise ValidationError(
            "Solo se puede generar la encuesta "
            "para una reserva cancelada."
        )

    # 4. Buscar si ya existe una encuesta
    encuesta = Encuesta.objects.filter(
        reserva=reserva,
        tipo=Encuesta.TIPO_CANCELACION
    ).first()

    if encuesta:
        return encuesta

    # 5. Crear una nueva encuesta
    encuesta = Encuesta(
        reserva=reserva,
        tipo=Encuesta.TIPO_CANCELACION
    )

    # 6. Ejecutar validaciones del modelo
    encuesta.full_clean()

    # 7. Guardar en PostgreSQL
    encuesta.save()

    return encuesta


def generar_encuesta_experiencia(reserva):

    # 1. Verificar que la reserva esté guardada
    if not reserva.pk:
        raise ValidationError(
            "La reserva debe estar guardada."
        )

    # 2. Obtener datos actualizados
    reserva.refresh_from_db(
        fields=["estado", "fin"]
    )

    # 3. Comprobar que no esté cancelada
    if reserva.estado != "CONFIRMADA":
        raise ValidationError(
            "Solo las reservas confirmadas "
            "pueden generar encuestas de experiencia."
        )

    # 4. Verificar que terminó el horario
    ahora = timezone.now()

    if ahora < reserva.fin:
        raise ValidationError(
            "La encuesta de experiencia solo "
            "estará disponible cuando termine "
            "el horario reservado."
        )

    # 5. Buscar una encuesta existente
    encuesta = Encuesta.objects.filter(
        reserva=reserva,
        tipo=Encuesta.TIPO_EXPERIENCIA
    ).first()

    if encuesta:
        return encuesta

    # 6. Crear la encuesta
    encuesta = Encuesta(
        reserva=reserva,
        tipo=Encuesta.TIPO_EXPERIENCIA
    )

    # 7. Validar y guardar
    encuesta.full_clean()
    encuesta.save()

    return encuesta



def obtener_encuestas_pendientes(cliente):

    # 1. Obtener la fecha y hora actual
    ahora = timezone.now()

    # 2. Buscar reservas del cliente cuyo horario terminó
    reservas = Reserva.objects.filter(
        cliente=cliente,
        estado="CONFIRMADA",
        fin__lte=ahora
    ).exclude(
        encuestas__tipo=Encuesta.TIPO_EXPERIENCIA
    )

    # 3. Generar encuestas de experiencia faltantes
    for reserva in reservas:
        generar_encuesta_experiencia(reserva)

    # 4. Obtener encuestas sin responder
    encuestas = Encuesta.objects.filter(
        reserva__cliente=cliente,
        respuesta__isnull=True
    ).select_related(
        "reserva__cancha__complejo"
    ).order_by("-fecha_creacion", "-id")

    return encuestas


@transaction.atomic
def responder_encuesta(encuesta, cliente, datos):

    # 1. Verificar autenticación
    if not cliente.is_authenticated:
        raise PermissionDenied(
            "Debes iniciar sesión para responder."
        )

    # 2. Verificar que la encuesta exista en BD
    if not encuesta.pk:
        raise ValidationError(
            "La encuesta debe estar guardada."
        )

    # 3. Actualizar el estado de la reserva
    reserva = encuesta.reserva
    reserva.refresh_from_db(fields=["estado", "fin"])

    # 4. Verificar que pertenezca al cliente
    if reserva.cliente_id != cliente.pk:
        raise PermissionDenied(
            "No puedes responder encuestas de otros clientes."
        )

    # 5. Verificar que la encuesta siga habilitada
    encuesta.full_clean()

    # 6. Comprobar que todavía no tenga respuesta
    if RespuestaEncuesta.objects.filter(
        encuesta=encuesta
    ).exists():
        raise ValidationError(
            "Esta encuesta ya fue respondida."
        )

    # 7. Crear el objeto con los datos recibidos
    respuesta = RespuestaEncuesta(
        encuesta=encuesta,
        motivo_cancelacion=datos.get(
            "motivo_cancelacion", ""
        ),
        hubiera_evitado=datos.get(
            "hubiera_evitado", ""
        ),
        calificacion=datos.get(
            "calificacion"
        ),
        volveria_reservar=datos.get(
            "volveria_reservar"
        ),
        aspecto_mejorar=datos.get(
            "aspecto_mejorar", ""
        ),
        comentario=datos.get(
            "comentario", ""
        )
    )

    # 8. Validar todos los campos
    respuesta.full_clean()

    # 9. Guardar en PostgreSQL
    respuesta.save()

    return respuesta
