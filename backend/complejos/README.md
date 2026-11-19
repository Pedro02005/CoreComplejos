# API del catálogo deportivo

Las consultas son públicas y de solo lectura. La creación y edición de datos
se realiza desde Django Admin.

| Método | Ruta | Respuesta |
| --- | --- | --- |
| GET | `/api/complejos/` | Lista paginada de complejos activos |
| GET | `/api/complejos/{id}/` | Complejo activo con sus canchas activas |
| GET | `/api/canchas/` | Lista paginada de canchas activas de complejos activos |
| GET | `/api/canchas/{id}/` | Cancha con horarios y tarifas activas |

## Filtros

- Complejos: `ciudad` (coincidencia exacta sin distinguir mayúsculas) y
  `nombre` (coincidencia parcial sin distinguir mayúsculas).
- Canchas: `complejo_id` (entero positivo), `deporte`, `ciudad` y `nombre`.
  Los filtros de texto funcionan como en complejos; `nombre` busca la cancha.
- Deportes: `FUTBOL`, `BASQUET`, `VOLEY`, `TENIS`, `PADEL`.
- Los filtros se pueden combinar. Por ejemplo:
  `/api/canchas/?complejo_id=5&deporte=FUTBOL&ciudad=Quito`.

Un filtro válido sin coincidencias devuelve una lista vacía. Los valores inválidos
(por ejemplo, `complejo_id=abc` o `deporte=OTRO`) devuelven HTTP 400.

## Paginación y datos

Ambos listados devuelven hasta 20 resultados por página, ordenados por nombre e
identificador. Para avanzar se utiliza `?page=2` o el enlace `next`:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 8,
      "nombre": "Cancha principal",
      "deporte": "FUTBOL",
      "capacidad": 10,
      "complejo": 5,
      "complejo_nombre": "Centro Norte",
      "ciudad": "Quito"
    }
  ]
}
```

Los complejos incluyen `id`, `nombre`, `descripcion`, `ciudad` y `direccion`.
El detalle de complejo añade `canchas`, con el formato del ejemplo anterior.

El detalle de cancha añade:

- `horarios`: `id`, `dia_semana`, `apertura`, `cierre`.
- `tarifas`: `id`, `dia_semana`, `inicio`, `fin`, `valor_hora`.

Los días van de 0 (lunes) a 6 (domingo), las horas usan `HH:MM:SS` y los importes
se expresan como texto decimal en USD, por ejemplo `"25.50"`. Si no hay horarios
o tarifas configurados, sus listas están vacías.

Los detalles de registros inexistentes o inactivos devuelven HTTP 404. Una cancha
de un complejo inactivo tampoco es accesible. Una página inexistente devuelve
HTTP 404 y los métodos de escritura devuelven HTTP 405.

## Disponibilidad y precio final

Que una cancha aparezca en el catálogo indica que está habilitada, pero no que
esté libre o tenga tarifas para cualquier intervalo. Después de seleccionarla,
se utiliza la API existente:

1. `GET /api/canchas/{id}/disponibilidad/?fecha=2026-11-22&duracion=90`
2. `POST /api/reservas/cotizar/`
3. `POST /api/reservas/` (requiere autenticación)

Las tarifas del catálogo son informativas. El precio final lo calcula la cotización
según el intervalo y las promociones aplicables.

## Verificación

Desde `backend/`, ejecutar `python manage.py test`. Django utiliza una base de
pruebas independiente de la base normal.
