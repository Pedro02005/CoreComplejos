from copy import copy

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Usuario
from .permisos import es_admin_complejo, es_admin_plataforma


def validar_usuario(usuario):
    """Reutiliza las reglas del modelo, incluida la cédula y el correo único."""
    try:
        usuario.full_clean(exclude=["password"])
    except DjangoValidationError as error:
        detalles = error.message_dict if hasattr(error, "message_dict") else {"non_field_errors": error.messages}
        if "__all__" in detalles:
            detalles["non_field_errors"] = detalles.pop("__all__")
        raise serializers.ValidationError(detalles)


class PerfilSerializer(serializers.ModelSerializer):
    es_administrador = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ("id", "username", "first_name", "last_name", "email", "cedula", "telefono", "rol", "es_administrador")
        read_only_fields = ("id", "username", "rol")

    def get_es_administrador(self, usuario):
        # También identifica al superusuario técnico, aunque conserve el rol inicial CLIENTE.
        return es_admin_plataforma(usuario) or es_admin_complejo(usuario)

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        usuario = copy(self.instance)
        for campo, valor in attrs.items():
            setattr(usuario, campo, valor)
        validar_usuario(usuario)
        if "cedula" in attrs:
            attrs["cedula"] = usuario.cedula
        return attrs

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError("El correo o la cédula ya está registrado.")


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmacion = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "cedula", "telefono", "password", "password_confirmacion")
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
        }

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmacion"]:
            raise serializers.ValidationError({"password_confirmacion": "Las contraseñas no coinciden."})
        # El registro público siempre crea clientes; nunca recibe roles ni privilegios.
        usuario = Usuario(**{campo: valor for campo, valor in attrs.items() if campo not in ("password", "password_confirmacion")})
        validar_usuario(usuario)
        try:
            validate_password(attrs["password"], usuario)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages})
        attrs["cedula"] = usuario.cedula
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirmacion")
        try:
            with transaction.atomic():
                return Usuario.objects.create_user(rol="CLIENTE", **validated_data)
        except IntegrityError:
            raise serializers.ValidationError("El usuario, correo o cédula ya está registrado.")
