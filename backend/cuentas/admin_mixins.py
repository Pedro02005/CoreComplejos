from .permisos import es_admin_plataforma, filtrar_por_complejo


class ComplejoRestringidoAdminMixin:
    """Limita listados, objetos y selectores al complejo del administrador."""

    campo_complejo = "complejo_id"

    def get_queryset(self, request):
        return filtrar_por_complejo(
            super().get_queryset(request), request.user, self.campo_complejo,
        )

    def _objeto_permitido(self, request, obj):
        return obj is None or self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._objeto_permitido(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._objeto_permitido(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._objeto_permitido(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ("complejo", "cancha"):
            campo = "pk" if db_field.name == "complejo" else "complejo_id"
            kwargs["queryset"] = filtrar_por_complejo(
                db_field.remote_field.model.objects.all(), request.user, campo,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_list_filter(self, request):
        filtros = super().get_list_filter(request)
        if es_admin_plataforma(request.user):
            return filtros
        # El selector de complejos no debe mostrar nombres de otras instalaciones.
        return [
            filtro for filtro in filtros
            if "complejo" not in (filtro if isinstance(filtro, str) else filtro[0])
        ]
