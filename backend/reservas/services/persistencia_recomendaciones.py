
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from reservas.models import (
    Recomendacion,
    EjecucionRegla
)

from .motor_reglas import generar_recomendaciones


REGLAS_IMPLEMENTADAS = (
    "R01",
    "R02",
    "R04",
    "R05"
)


@transaction.atomic
def guardar_recomendaciones(cliente, dias=90):

    # 1. Ejecutar el motor de reglas
    resultado = generar_recomendaciones(
        cliente,
        dias
    )

    ahora = timezone.now()

    # 2. Organizar recomendaciones por regla
    datos_por_regla = {
        item["regla"]: item
        for item in resultado["recomendaciones"]
    }

    # 3. Desactivar recomendaciones vencidas
    Recomendacion.objects.filter(
        cliente=cliente,
        regla__in=REGLAS_IMPLEMENTADAS,
        activa=True,
        vence_en__lte=ahora
    ).update(activa=False)

    # 4. Desactivar reglas que ya no se cumplen
    Recomendacion.objects.filter(
        cliente=cliente,
        regla__in=REGLAS_IMPLEMENTADAS,
        activa=True
    ).exclude(
        regla__in=datos_por_regla.keys()
    ).update(activa=False)

    recomendaciones_guardadas = []
    nuevas = 0

    # 5. Registrar cada regla implementada
    for codigo in REGLAS_IMPLEMENTADAS:

        datos = datos_por_regla.get(codigo)

        if datos:

            # Buscar recomendación vigente
            recomendacion = (
                Recomendacion.objects.filter(
                    cliente=cliente,
                    regla=codigo,
                    activa=True,
                    vence_en__gt=ahora
                ).order_by("-id").first()
            )

            # 6. Comprobar si cambió la recomendación
            if recomendacion:

                campos = (
                    "categoria",
                    "titulo",
                    "motivo",
                    "accion_sugerida",
                    "prioridad"
                )

                cambio = any(
                    getattr(recomendacion, campo)
                    != datos[campo]
                    for campo in campos
                )

                if cambio:
                    recomendacion.activa = False
                    recomendacion.save(
                        update_fields=["activa"]
                    )
                    recomendacion = None

            # 7. Crear solamente si hace falta
            if recomendacion is None:

                recomendacion = Recomendacion(
                    cliente=cliente,
                    regla=codigo,
                    categoria=datos["categoria"],
                    titulo=datos["titulo"],
                    motivo=datos["motivo"],
                    accion_sugerida=datos["accion_sugerida"],
                    prioridad=datos["prioridad"],
                    vence_en=(
                        ahora + timedelta(days=7)
                    ),
                    activa=True
                )

                recomendacion.full_clean()
                recomendacion.save()

                nuevas += 1

            recomendaciones_guardadas.append(
                recomendacion
            )

            # 8. Registrar una regla cumplida
            ejecucion = EjecucionRegla(
                cliente=cliente,
                regla=codigo,
                cumplida=True,
                detalle=(
                    f"Regla {codigo} cumplida. "
                    f"{datos['motivo']}"
                ),
                recomendacion=recomendacion
            )

        else:

            # 9. Registrar una regla no cumplida
            ejecucion = EjecucionRegla(
                cliente=cliente,
                regla=codigo,
                cumplida=False,
                detalle=(
                    f"Regla {codigo} no cumplida "
                    f"en el período de {dias} días."
                ),
                recomendacion=None
            )

        # 10. Validar y guardar la ejecución
        ejecucion.full_clean()
        ejecucion.save()

    # 11. Ordenar las recomendaciones
    recomendaciones_guardadas.sort(
        key=lambda r: (r.prioridad, r.regla)
    )

    return {
        "periodo_dias": dias,
        "recomendaciones": recomendaciones_guardadas,
        "nuevas": nuevas,
        "ejecuciones_registradas": len(
            REGLAS_IMPLEMENTADAS
        )
    }
