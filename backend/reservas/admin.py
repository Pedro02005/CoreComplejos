
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from cuentas.admin_mixins import ComplejoRestringidoAdminMixin
from .forms import CancelacionActionForm
from .services.cancelacion import cancelar_reserva

from .models import (
    Reserva,
    DetallePrecio,
    HistorialReserva,
    Encuesta,
    RespuestaEncuesta
)

from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    Recomendacion,
    EjecucionRegla,
    Promocion,
    AsignacionPromocion,
)




# Clase base para mostrar registros sin modificarlos
class SoloLecturaInline(admin.TabularInline):

    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Mostrar las tarifas históricas de una reserva
class DetallePrecioInline(SoloLecturaInline):

    model = DetallePrecio

    fields = (
        "tarifa",
        "inicio",
        "fin",
        "valor_hora",
        "subtotal",
    )

    readonly_fields = fields

    verbose_name = "Detalle de precio"
    verbose_name_plural = "Detalles de precio"


# Mostrar el historial de eventos
class HistorialReservaInline(SoloLecturaInline):

    model = HistorialReserva

    fields = (
        "fecha",
        "evento",
        "actor",
        "estado_anterior",
        "estado_nuevo",
        "motivo",
    )

    readonly_fields = fields

    verbose_name = "Evento del historial"
    verbose_name_plural = "Historial de la reserva"


# Administración principal de reservas
@admin.register(Reserva)
class ReservaAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    campo_complejo = "cancha__complejo_id"
    action_form = CancelacionActionForm
    actions = ("cancelar_reservas",)

    list_display = (
        "id",
        "cliente",
        "complejo",
        "cancha",
        "inicio",
        "fin",
        "estado",
        "total",
    )

    list_filter = (
        "estado",
        "cancha__complejo",
        "inicio",
    )

    search_fields = (
        "cliente__username",
        "cliente__email",
        "cancha__nombre",
        "cancha__complejo__nombre",
    )

    list_select_related = (
        "cliente",
        "cancha__complejo",
    )

    ordering = ("-inicio",)

    date_hierarchy = "inicio"

    # Mostrar los modelos relacionados
    inlines = [
        DetallePrecioInline,
        HistorialReservaInline,
    ]

    # Campos que mostraremos en el detalle
    fields = (
        "id",
        "cliente",
        "cancha",
        "inicio",
        "fin",
        "estado",
        "total",
        "clave_solicitud",
        "cancelable_hasta",
    )

    readonly_fields = fields

    @admin.display(
        description="Complejo",
        ordering="cancha__complejo__nombre"
    )
    def complejo(self, obj):
        return obj.cancha.complejo.nombre

    # No crear reservas directamente desde Admin
    def has_add_permission(self, request):
        return False

    # No modificar reservas directamente desde Admin
    def has_change_permission(self, request, obj=None):
        return False

    # No eliminar reservas desde Admin
    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Cancelar reservas seleccionadas", permissions=["view"])
    def cancelar_reservas(self, request, queryset):
        motivo = (request.POST.get("motivo") or "").strip()
        if not motivo or len(motivo) > 500:
            self.message_user(request, "Indica un motivo de entre 1 y 500 caracteres.", messages.ERROR)
            return
        canceladas = 0
        for reserva in queryset:
            try:
                cancelar_reserva(reserva, request.user, motivo)
            except (ValidationError, PermissionDenied) as error:
                detalle = "; ".join(error.messages) if isinstance(error, ValidationError) else str(error)
                self.message_user(request, f"Reserva {reserva.pk}: {detalle}", messages.ERROR)
            else:
                canceladas += 1
        if canceladas:
            self.message_user(request, f"Reservas canceladas: {canceladas}.", messages.SUCCESS)



class RespuestaEncuestaInline(SoloLecturaInline):

    model = RespuestaEncuesta

    fields = (
        "motivo_cancelacion",
        "hubiera_evitado",
        "calificacion",
        "volveria_reservar",
        "aspecto_mejorar",
        "comentario",
        "fecha_respuesta",
    )

    readonly_fields = fields

    verbose_name = "Respuesta"
    verbose_name_plural = "Respuesta de la encuesta"



@admin.register(Encuesta)
class EncuestaAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    campo_complejo = "reserva__cancha__complejo_id"

    list_display = (
        "id",
        "tipo",
        "reserva",
        "cliente",
        "complejo",
        "respondida",
        "fecha_creacion",
    )

    list_filter = (
        "tipo",
        "fecha_creacion",
    )

    search_fields = (
        "reserva__cliente__username",
        "reserva__cliente__email",
        "reserva__cancha__nombre",
        "reserva__cancha__complejo__nombre",
    )

    list_select_related = (
        "reserva__cliente",
        "reserva__cancha__complejo",
        "respuesta",
    )

    ordering = ("-fecha_creacion",)

    fields = (
        "id",
        "reserva",
        "tipo",
        "fecha_creacion",
    )

    readonly_fields = fields

    inlines = [RespuestaEncuestaInline]

    @admin.display(
        description="Cliente",
        ordering="reserva__cliente__username"
    )
    def cliente(self, obj):
        return obj.reserva.cliente.username

    @admin.display(
        description="Complejo",
        ordering="reserva__cancha__complejo__nombre"
    )
    def complejo(self, obj):
        return obj.reserva.cancha.complejo.nombre

    @admin.display(
        boolean=True,
        description="Respondida"
    )
    def respondida(self, obj):
        return hasattr(obj, "respuesta")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



class AdminSoloConsulta(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



@admin.register(Recomendacion)
class RecomendacionAdmin(AdminSoloConsulta):

    list_display = (
        "id",
        "cliente",
        "regla",
        "categoria",
        "titulo",
        "prioridad",
        "activa",
        "vigente",
        "fecha_creacion",
    )

    list_filter = (
        "regla",
        "categoria",
        "activa",
    )

    search_fields = (
        "cliente__username",
        "cliente__email",
        "titulo",
        "motivo",
    )

    list_select_related = ("cliente",)

    ordering = ("-fecha_creacion", "-id")

    fields = (
        "id",
        "cliente",
        "regla",
        "categoria",
        "titulo",
        "motivo",
        "accion_sugerida",
        "prioridad",
        "activa",
        "fecha_creacion",
        "vence_en",
    )

    readonly_fields = fields

    @admin.display(
        boolean=True,
        description="Vigente"
    )
    def vigente(self, obj):
        return (
            obj.activa
            and obj.vence_en > timezone.now()
        )



@admin.register(EjecucionRegla)
class EjecucionReglaAdmin(AdminSoloConsulta):

    list_display = (
        "id",
        "cliente",
        "regla",
        "cumplida",
        "recomendacion",
        "fecha_ejecucion",
    )

    list_filter = (
        "regla",
        "cumplida",
        "fecha_ejecucion",
    )

    search_fields = (
        "cliente__username",
        "cliente__email",
        "detalle",
    )

    list_select_related = (
        "cliente",
        "recomendacion",
    )

    ordering = ("-fecha_ejecucion", "-id")

    fields = (
        "id",
        "cliente",
        "regla",
        "cumplida",
        "detalle",
        "recomendacion",
        "fecha_ejecucion",
    )

    readonly_fields = fields



@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "codigo",
        "nombre",
        "regla_objetivo",
        "tipo_descuento",
        "valor_descuento",
        "usos_realizados",
        "activa",
        "fecha_fin",
    )

    list_filter = (
        "tipo_descuento",
        "regla_objetivo",
        "activa",
    )

    search_fields = (
        "codigo",
        "nombre",
        "descripcion",
    )

    ordering = ("-fecha_inicio", "-id")

    fields = (
        "nombre",
        "codigo",
        "descripcion",
        "tipo_descuento",
        "valor_descuento",
        "regla_objetivo",
        "fecha_inicio",
        "fecha_fin",
        "limite_usos",
        "activa",
    )

    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        return queryset.annotate(
            usos_confirmados=Count(
                "asignaciones",
                filter=Q(
                    asignaciones__estado="UTILIZADA"
                )
            )
        )

    @admin.display(
        description="Usos realizados"
    )
    def usos_realizados(self, obj):

        limite = (
            obj.limite_usos
            if obj.limite_usos is not None
            else "Sin límite"
        )

        return f"{obj.usos_confirmados} / {limite}"

    def get_readonly_fields(self, request, obj=None):

        # Conservar las condiciones originales
        # de una campaña que ya fue utilizada
        if obj and obj.asignaciones.filter(
            estado="UTILIZADA"
        ).exists():

            return (
                "codigo",
                "tipo_descuento",
                "valor_descuento",
                "regla_objetivo",
            )

        return ()

    def has_delete_permission(self, request, obj=None):
        return False



@admin.register(AsignacionPromocion)
class AsignacionPromocionAdmin(AdminSoloConsulta):

    list_display = (
        "id",
        "cliente",
        "promocion",
        "estado",
        "recomendacion",
        "reserva_utilizada",
        "descuento_aplicado",
        "fecha_asignacion",
    )

    list_filter = (
        "estado",
        "promocion",
        "fecha_asignacion",
    )

    search_fields = (
        "cliente__username",
        "cliente__email",
        "promocion__codigo",
    )

    list_select_related = (
        "cliente",
        "promocion",
        "recomendacion",
        "reserva_utilizada",
    )

    ordering = ("-fecha_asignacion", "-id")

    fields = (
        "id",
        "cliente",
        "promocion",
        "recomendacion",
        "motivo_asignacion",
        "estado",
        "fecha_asignacion",
        "fecha_uso",
        "reserva_utilizada",
        "descuento_aplicado",
    )

    readonly_fields = fields
