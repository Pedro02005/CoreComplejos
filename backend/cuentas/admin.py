from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario
from .permisos import es_admin_plataforma


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "cedula",
            "telefono",
            "rol",
            "complejo",
        )


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):

    add_form = UsuarioCreationForm

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "cedula",
        "rol",
        "complejo",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "cedula",
        "first_name",
        "last_name",
    )

    list_filter = (
        "rol",
        "is_active",
        "is_staff",
    )
    list_select_related = ("complejo",)
    autocomplete_fields = ("complejo",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Información adicional",
            {
                "fields": (
                    "cedula",
                    "telefono",
                    "rol",
                    "complejo",
                )
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "cedula",
                    "telefono",
                    "rol",
                    "complejo",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        usuarios = super().get_queryset(request)
        if request.user.is_superuser:
            return usuarios
        if es_admin_plataforma(request.user):
            return usuarios.filter(is_superuser=False, rol__in=["CLIENTE", "ADMIN_COMPLEJO"])
        return usuarios.none()

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (
            obj is None or request.user.is_superuser
            or (not obj.is_superuser and obj.rol in ("CLIENTE", "ADMIN_COMPLEJO"))
        )

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and (
            obj is None or request.user.is_superuser
            or (not obj.is_superuser and obj.rol in ("CLIENTE", "ADMIN_COMPLEJO"))
        )

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return super().get_fieldsets(request, obj)
        return (
            (None, {"fields": ("username", "password")}),
            ("Datos personales", {"fields": ("first_name", "last_name", "email", "cedula", "telefono")}),
            ("Acceso", {"fields": ("rol", "complejo", "is_active")}),
        )

    def get_form(self, request, obj=None, **kwargs):
        formulario = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and "rol" in formulario.base_fields:
            formulario.base_fields["rol"].choices = [
                opcion for opcion in Usuario.ROLES if opcion[0] in ("CLIENTE", "ADMIN_COMPLEJO")
            ]
        return formulario
