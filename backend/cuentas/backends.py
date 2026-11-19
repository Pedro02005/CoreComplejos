from django.contrib.auth.backends import ModelBackend

from .permisos import es_admin_complejo, es_admin_plataforma


def permisos_modelos(app, modelos, acciones):
    return {f"{app}.{accion}_{modelo}" for modelo in modelos for accion in acciones}


LECTURA_RESERVAS = permisos_modelos(
    "reservas",
    ("reserva", "detalleprecio", "historialreserva", "encuesta", "respuestaencuesta"),
    ("view",),
)
GESTION_INSTALACIONES = permisos_modelos(
    "complejos", ("cancha", "horarioatencion", "tarifa", "bloqueo"),
    ("view", "add", "change"),
)


class RolesBackend(ModelBackend):
    """Conserva el login de Django y concede permisos explícitos por rol.

    Los administradores usan los roles, sin configurar grupos manualmente.
    El filtrado de registros se realiza además en cada ModelAdmin y en la API.
    """

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active or obj is not None:
            return set()
        if user_obj.is_superuser:
            return super().get_all_permissions(user_obj, obj)
        if es_admin_plataforma(user_obj):
            return (
                LECTURA_RESERVAS | GESTION_INSTALACIONES
                | permisos_modelos("complejos", ("complejo",), ("view", "add", "change"))
                | permisos_modelos("cuentas", ("usuario",), ("view", "add", "change"))
                | permisos_modelos("reservas", ("promocion",), ("view", "add", "change"))
                | permisos_modelos(
                    "reservas", ("recomendacion", "ejecucionregla", "asignacionpromocion"),
                    ("view",),
                )
            )
        if es_admin_complejo(user_obj):
            return LECTURA_RESERVAS | GESTION_INSTALACIONES | {"complejos.view_complejo", "complejos.change_complejo"}
        return set()

    async def aget_all_permissions(self, user_obj, obj=None):
        if user_obj.is_authenticated and user_obj.is_active and user_obj.is_superuser:
            return await super().aget_all_permissions(user_obj, obj)
        return self.get_all_permissions(user_obj, obj)
