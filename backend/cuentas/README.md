# Roles y administración de complejos

## Relación uno a muchos

`Usuario.complejo` es una clave foránea a `Complejo`. Cada administrador tiene
un solo complejo y un complejo puede tener varios administradores. No hay una
tabla intermedia de asignaciones.

La validación del modelo y una restricción de la base de datos exigen:

- `ADMIN_COMPLEJO`: un complejo obligatorio.
- `CLIENTE` y `ADMIN_PLATAFORMA`: sin complejo asignado.

El complejo no se puede eliminar mientras tenga administradores asociados.
Los registros existentes se conservan al aplicar la migración.

## Acceso por rol

| Función | Cliente | Administrador de complejo | Administrador de plataforma |
| --- | --- | --- | --- |
| Catálogo y disponibilidad públicos | Sí | Sí | Sí |
| Django Admin | No | Sí | Sí |
| Ver y editar complejos | No | El asignado | Todos |
| Crear complejos | No | No | Sí |
| Crear y editar canchas, horarios, tarifas y bloqueos | No | De su complejo | De todos |
| Consultar reservas por API | Propias | De su complejo | Todas |
| Consultar encuestas en Admin | No | De su complejo | Todas |
| Cancelar reservas | Propias, con 12 h de anticipación | De su complejo, antes del inicio y con motivo | Todas, antes del inicio y con motivo |
| Gestionar clientes y administradores de complejo | No | No | Sí |
| Gestionar campañas de promociones | No | No | Sí |
| Consultar recomendaciones y asignaciones en Admin | No | No | Sí |

La eliminación de registros no se concede a los roles administrativos: se usan
los campos de activo/inactivo para conservar referencias e historial. Las reservas,
encuestas y resultados de personalización mantienen su edición directa bloqueada.

Los endpoints de encuestas, promociones y recomendaciones personales continúan
mostrando los datos del usuario autenticado. La creación de reservas continúa
utilizando al usuario autenticado como cliente.

## Crear un administrador

1. Entrar en `/admin/` como superusuario técnico o administrador de plataforma.
2. Abrir **Usuarios**, agregar una cuenta y completar usuario, correo y contraseña.
3. Elegir `ADMIN_COMPLEJO` y seleccionar el complejo correspondiente.
4. Guardar. El usuario ya puede entrar en `/admin/` con sus credenciales.

El acceso `is_staff` se sincroniza al guardar según el rol, sin convertir la cuenta
en superusuario. No hace falta asignar grupos ni permisos manuales. Una cuenta
inactiva no puede iniciar sesión. Si se cambia un administrador a cliente, hay que
quitar su complejo; al guardar pierde el acceso administrativo. Reasignar su complejo
cambia el alcance de sus siguientes solicitudes.

Solo el superusuario técnico crea cuentas `ADMIN_PLATAFORMA`. Los administradores
de plataforma pueden gestionar clientes y administradores de complejo, pero no
modificar cuentas de plataforma, superusuarios, grupos o privilegios técnicos.

El superusuario conserva las capacidades técnicas de Django. Las restricciones
existentes de solo lectura sobre reservas y resultados siguen aplicándose.

## Cancelar desde Django Admin

En la lista de **Reservas**, seleccionar las reservas, escribir el motivo en
**Motivo de cancelación** y ejecutar **Cancelar reservas seleccionadas**.
La acción usa el mismo servicio de cancelación que la API, conserva el actor y
el motivo en el historial y genera la encuesta de cancelación. Si una reserva
ya comenzó o ya está cancelada, se informa del error. Si se seleccionan varias,
las válidas se cancelan y las que incumplen las reglas permanecen sin cambios.

## Archivos principales para explicar el funcionamiento

- `models.py`: relación con el complejo, validación y acceso staff.
- `permisos.py`: alcance por complejo y visibilidad de reservas, compartidos por
  Django Admin y la API.
- `backends.py`: inicio de sesión de Django y permisos de modelo derivados del rol.
  Los permisos manuales no amplían los permisos administrativos definidos para el rol.
- `admin_mixins.py`: filtrado de listados, accesos directos, selectores y filtros.
- `admin.py`: asignación de roles y protección de cuentas privilegiadas.
- `../complejos/admin.py`: gestión de instalaciones y formularios del complejo.
- `../reservas/admin.py`: consulta de reservas y encuestas, y acción de cancelación.

Los autocompletados y el selector de canchas por complejo también aplican el
alcance del administrador. La API de catálogo sigue siendo pública y de solo lectura.

## Instalación y pruebas

Desde `backend/`, con el entorno virtual activo:

```text
python manage.py migrate
python manage.py test
```

La migración añade el campo opcional y la restricción de coherencia con el rol.
Las pruebas comprueban las asignaciones, los permisos, los formularios, los accesos
directos, los autocompletados y las cancelaciones. Usan una base de pruebas separada.
