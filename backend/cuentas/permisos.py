"""Reglas compartidas por la API y Django Admin."""


def es_admin_plataforma(usuario):
    return usuario.is_authenticated and usuario.is_active and (
        usuario.is_superuser
        or (usuario.is_staff and usuario.rol == "ADMIN_PLATAFORMA")
    )


def es_admin_complejo(usuario):
    return (
        usuario.is_authenticated and usuario.is_active and usuario.is_staff
        and usuario.rol == "ADMIN_COMPLEJO" and usuario.complejo_id is not None
    )


def puede_administrar_complejo(usuario, complejo_id):
    return es_admin_plataforma(usuario) or (
        es_admin_complejo(usuario) and usuario.complejo_id == complejo_id
    )


def filtrar_por_complejo(queryset, usuario, campo):
    if es_admin_plataforma(usuario):
        return queryset
    if es_admin_complejo(usuario):
        return queryset.filter(**{campo: usuario.complejo_id})
    return queryset.none()


def reservas_visibles(queryset, usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return queryset.none()
    if es_admin_plataforma(usuario) or es_admin_complejo(usuario):
        return filtrar_por_complejo(queryset, usuario, "cancha__complejo_id")
    if usuario.rol == "CLIENTE":
        return queryset.filter(cliente=usuario)
    return queryset.none()
