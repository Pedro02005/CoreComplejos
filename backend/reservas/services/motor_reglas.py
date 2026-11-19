
from .estadisticas import obtener_estadisticas_encuestas

from .historial_estadisticas import (
    obtener_estadisticas_historial
)


def evaluar_reglas(estadisticas_encuestas, estadisticas_historial):

    recomendaciones = []

    # 1. Obtener los datos calculados
    cancelaciones = estadisticas_encuestas["cancelaciones"]
    experiencias = estadisticas_encuestas["experiencias"]

    ultima_cancelacion = (
        cancelaciones["ultima_respuesta"] or {}
    )

    ultima_experiencia = (
        experiencias["ultima_respuesta"] or {}
    )

    franja_preferida = (
        estadisticas_historial["franja_preferida"] or {}
    )

    # -------------------------------------
    # R01: PROBLEMAS CON EL PRECIO
    # -------------------------------------

    if (
        ultima_cancelacion.get("motivo_cancelacion") == "PRECIO"
        and ultima_cancelacion.get("hubiera_evitado") == "DESCUENTO"
    ):

        recomendaciones.append({
            "regla": "R01",
            "prioridad": 2,
            "categoria": "PRECIO",
            "titulo": "Opciones más económicas",
            "motivo": (
                "Tu última encuesta de cancelación "
                "indica que el precio fue un problema "
                "y que un descuento habría ayudado."
            ),
            "accion_sugerida": "EVALUAR_DESCUENTO"
        })

    # -------------------------------------
    # R02: PROBLEMAS CON EL HORARIO
    # -------------------------------------

    if (
        ultima_cancelacion.get("motivo_cancelacion") == "HORARIO"
        and ultima_cancelacion.get("hubiera_evitado") == "CAMBIO_HORARIO"
    ):

        codigo_franja = franja_preferida.get("codigo")

        nombres_franjas = {
            "MANANA": "la mañana",
            "TARDE": "la tarde",
            "NOCHE": "la noche"
        }

        franja_texto = nombres_franjas.get(
            codigo_franja,
            "otros horarios"
        )

        recomendaciones.append({
            "regla": "R02",
            "prioridad": 3,
            "categoria": "HORARIO",
            "titulo": "Explorar horarios alternativos",
            "motivo": (
                "Tu última encuesta de cancelación "
                "indica dificultades con el horario. "
                f"Podemos priorizar opciones en {franja_texto}."
            ),
            "accion_sugerida": "BUSCAR_OTROS_HORARIOS"
        })

    # -------------------------------------
    # R04: MALA EXPERIENCIA
    # -------------------------------------

    calificacion = ultima_experiencia.get("calificacion")

    if calificacion is not None and calificacion <= 2:

        aspecto = ultima_experiencia.get("aspecto_mejorar")

        if aspecto == "INSTALACIONES":
            accion = "BUSCAR_OTRA_CANCHA"
            titulo = "Explorar otras instalaciones"

        else:
            accion = "BUSCAR_ALTERNATIVAS"
            titulo = "Mejorar tu próxima experiencia"

        recomendaciones.append({
            "regla": "R04",
            "prioridad": 1,
            "categoria": "EXPERIENCIA",
            "titulo": titulo,
            "motivo": (
                f"Tu última experiencia recibió "
                f"una calificación de {calificacion}/5. "
                "Queremos ayudarte a encontrar "
                "una mejor alternativa."
            ),
            "accion_sugerida": accion
        })

    # -------------------------------------
    # R05: FIDELIZACION
    # -------------------------------------

    total_reservas = estadisticas_historial[
        "reservas_finalizadas"
    ]

    promedio = experiencias["calificacion_promedio"]

    muestra_suficiente = experiencias["muestra_suficiente"]

    if (
        total_reservas >= 3
        and muestra_suficiente
        and promedio is not None
        and promedio >= 4
    ):

        recomendaciones.append({
            "regla": "R05",
            "prioridad": 4,
            "categoria": "FIDELIZACION",
            "titulo": "Beneficio por fidelidad",
            "motivo": (
                f"Registras {total_reservas} reservas "
                "confirmadas con horario concluido "
                "y una satisfacción promedio "
                f"de {promedio}/5."
            ),
            "accion_sugerida": "EVALUAR_BENEFICIO_FIDELIDAD"
        })

    # 2. Ordenar por prioridad
    recomendaciones.sort(
        key=lambda r: (r["prioridad"], r["regla"])
    )

    return recomendaciones


def generar_recomendaciones(cliente, dias=90):

    # 1. Obtener estadísticas de encuestas
    estadisticas_encuestas = obtener_estadisticas_encuestas(
        cliente,
        dias
    )

    # 2. Obtener estadísticas del historial
    estadisticas_historial = obtener_estadisticas_historial(
        cliente,
        dias
    )

    # 3. Evaluar las reglas
    recomendaciones = evaluar_reglas(
        estadisticas_encuestas,
        estadisticas_historial
    )

    # 4. Devolver el resultado
    return {
        "periodo_dias": dias,
        "cantidad_recomendaciones": len(recomendaciones),
        "recomendaciones": recomendaciones
    }
