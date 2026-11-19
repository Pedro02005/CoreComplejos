from django.contrib import admin

from .models import (
    Complejo,
    Cancha,
    HorarioAtencion,
    Tarifa,
    Bloqueo,
)

from django.urls import path
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from .forms import TarifaAdminForm
from cuentas.admin_mixins import ComplejoRestringidoAdminMixin
from cuentas.permisos import filtrar_por_complejo, puede_administrar_complejo


class CanchaInline(admin.TabularInline):
    model = Cancha
    extra = 1
    fields = (
        "nombre",
        "deporte",
        "capacidad",
        "activa",
    )

    def get_queryset(self, request):
        return filtrar_por_complejo(super().get_queryset(request), request.user, "complejo_id")

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and (
            obj is None or puede_administrar_complejo(request.user, obj.pk)
        )

    def has_add_permission(self, request, obj=None):
        return super().has_add_permission(request, obj) and (
            obj is None or puede_administrar_complejo(request.user, obj.pk)
        )

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (
            obj is None or puede_administrar_complejo(request.user, obj.pk)
        )


@admin.register(Complejo)
class ComplejoAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    campo_complejo = "pk"
    ordering = ("nombre", "pk")

    list_display = (
        "id",
        "nombre",
        "ciudad",
        "activo",
    )

    search_fields = (
        "nombre",
        "ciudad",
    )

    list_filter = (
        "ciudad",
        "activo",
    )

    inlines = [CanchaInline]


@admin.register(Cancha)
class CanchaAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    ordering = ("nombre", "pk")

    list_display = (
        "id",
        "nombre",
        "complejo",
        "deporte",
        "capacidad",
        "activa",
    )

    search_fields = (
        "nombre",
        "complejo__nombre",
    )

    list_filter = (
        "complejo",
        "deporte",
        "activa",
    )

    autocomplete_fields = ["complejo"]
    

@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    campo_complejo = "cancha__complejo_id"

    list_display = (
        "cancha",
        "dia_semana",
        "apertura",
        "cierre",
    )

    list_filter = ("dia_semana", "cancha__complejo")

    search_fields = (
        "cancha__nombre",
        "cancha__complejo__nombre",
    )

    autocomplete_fields = ["cancha"]


@admin.register(Tarifa)
class TarifaAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    campo_complejo = "cancha__complejo_id"

    form = TarifaAdminForm

    list_display = (
        "cancha",
        "dia_semana",
        "inicio",
        "fin",
        "valor_hora",
        "activa",
    )

    list_filter = (
        "dia_semana",
        "activa",
        "cancha__complejo",
    )

    search_fields = (
        "cancha__nombre",
        "cancha__complejo__nombre",
    )

    fields = (
        "complejo",
        "cancha",
        "dia_semana",
        "inicio",
        "fin",
        "valor_hora",
        "activa",
    )

    class Media:
        js = ("complejos/js/tarifas.js",)

    def get_form(self, request, obj=None, **kwargs):
        formulario = super().get_form(request, obj, **kwargs)

        class FormularioConUsuario(formulario):
            def __init__(self, *args, **form_kwargs):
                form_kwargs["usuario"] = request.user
                super().__init__(*args, **form_kwargs)

        return FormularioConUsuario

    def get_urls(self):

        urls = super().get_urls()

        nuevas_urls = [
            path(
                "canchas-por-complejo/",
                self.admin_site.admin_view(
                    self.canchas_por_complejo
                ),
                name="complejos_tarifa_canchas"
            ),
        ]

        return nuevas_urls + urls

    def canchas_por_complejo(self, request):

        if not (
            self.has_add_permission(request)
            or self.has_change_permission(request)
        ):
            raise PermissionDenied

        complejo_id = request.GET.get("complejo_id")

        if complejo_id and str(complejo_id).isdigit():
            canchas = filtrar_por_complejo(Cancha.objects.all(), request.user, "complejo_id").filter(
                complejo_id=complejo_id
            ).order_by("nombre")
        else:
            canchas = Cancha.objects.none()

        datos = [
            {
                "id": cancha.id,
                "nombre": cancha.nombre,
            }
            for cancha in canchas
        ]

        return JsonResponse({"canchas": datos})


@admin.register(Bloqueo)
class BloqueoAdmin(ComplejoRestringidoAdminMixin, admin.ModelAdmin):

    campo_complejo = "cancha__complejo_id"
    readonly_fields = ("administrador",)

    list_display = (
        "cancha",
        "inicio",
        "fin",
        "motivo",
        "activo",
    )

    list_filter = (
        "activo",
        "cancha__complejo",
    )

    search_fields = (
        "cancha__nombre",
        "motivo",
    )

    autocomplete_fields = ["cancha"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.administrador = request.user
        super().save_model(request, obj, form, change)
