
from django.db import transaction
from django.utils import timezone

from reservas.models import (
    Promocion,
    AsignacionPromocion
)

from .persistencia_recomendaciones import (
    guardar_recomendaciones
)


REGLAS_PROMOCIONABLES = {
    "R01": "EVALUAR_DESCUENTO",
    "R05": "EVALUAR_BENEFICIO_FIDELIDAD",
}


@transaction.atomic
def asignar_promociones_personalizadas(cliente, dias=90):

    # 1. Actualizar las recomendaciones del cliente
    resultado = guardar_recomendaciones(
        cliente,
        dias
    )

    ahora = timezone.now()

    asignaciones = []
    nuevas = 0
    reglas_sin_campana = []

    # 2. Recorrer las recomendaciones vigentes
    for recomendacion in resultado["recomendaciones"]:

        regla = recomendacion.regla

        # Solo automatizamos R01 y R05
        if regla not in REGLAS_PROMOCIONABLES:
            continue

        # Validar que la acción sea promocionable
        if (
            recomendacion.accion_sugerida
            != REGLAS_PROMOCIONABLES[regla]
        ):
            continue

        # 3. Comprobar si ya tiene una promoción
        # disponible y vigente para esta regla
        existente = AsignacionPromocion.objects.filter(
            cliente=cliente,
            estado="DISPONIBLE",
            promocion__regla_objetivo=regla,
            promocion__activa=True,
            promocion__fecha_inicio__lte=ahora,
            promocion__fecha_fin__gt=ahora
        ).select_related(
            "promocion"
        ).first()

        if existente:
            asignaciones.append(existente)
            continue

        # 4. Buscar campañas compatibles
        promociones = Promocion.objects.filter(
            regla_objetivo=regla,
            activa=True,
            fecha_inicio__lte=ahora,
            fecha_fin__gt=ahora
        ).order_by(
            "fecha_fin",
            "id"
        )

        asignada = False

        # 5. Evaluar las campañas disponibles
        for promocion in promociones:

            # Comprobar el límite global de usos
            usos = AsignacionPromocion.objects.filter(
                promocion=promocion,
                estado="UTILIZADA"
            ).count()

            if (
                promocion.limite_usos is not None
                and usos >= promocion.limite_usos
            ):
                continue

            # No asignar dos veces la misma campaña
            ya_asignada = AsignacionPromocion.objects.filter(
                cliente=cliente,
                promocion=promocion
            ).exists()

            if ya_asignada:
                continue

            # 6. Crear la asignación personalizada
            asignacion = AsignacionPromocion(
                cliente=cliente,
                promocion=promocion,
                recomendacion=recomendacion,
                motivo_asignacion=recomendacion.motivo,
                estado="DISPONIBLE"
            )

            asignacion.full_clean()
            asignacion.save()

            asignaciones.append(asignacion)

            nuevas += 1
            asignada = True

            # Una campaña por regla en esta ejecución
            break

        if not asignada:
            reglas_sin_campana.append(regla)

    return {
        "nuevas": nuevas,
        "cantidad_asignaciones": len(asignaciones),
        "asignaciones": asignaciones,
        "reglas_sin_campana": reglas_sin_campana
    }
