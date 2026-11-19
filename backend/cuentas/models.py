from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower

from .validators import validar_cedula, validar_telefono


class Usuario(AbstractUser):

    ROLES = [
        ("CLIENTE", "Cliente"),
        ("ADMIN_COMPLEJO", "Administrador de complejo"),
        ("ADMIN_PLATAFORMA", "Administrador de plataforma"),
    ]

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()]
    )

    cedula = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_cedula]
    )

    telefono = models.CharField(
        max_length=10,
        blank=True,
        validators=[validar_telefono]
    )

    rol = models.CharField(
        max_length=20,
        choices=ROLES,
        default="CLIENTE"
    )

    complejo = models.ForeignKey(
        "complejos.Complejo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="administradores",
        help_text="Obligatorio únicamente para administradores de complejo.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="usuario_email_unico_sin_mayusculas"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(rol="ADMIN_COMPLEJO", complejo__isnull=False)
                    | models.Q(
                        rol__in=["CLIENTE", "ADMIN_PLATAFORMA"],
                        complejo__isnull=True,
                    )
                ),
                name="usuario_complejo_segun_rol",
            ),
        ]

    def clean(self):
        super().clean()

        if self.email:
            self.email = self.email.strip().lower()

        if self.cedula == "":
            self.cedula = None

        if self.rol == "ADMIN_COMPLEJO" and not self.complejo_id:
            raise ValidationError({"complejo": "El administrador debe tener un complejo asignado."})
        if self.rol != "ADMIN_COMPLEJO" and self.complejo_id:
            raise ValidationError({"complejo": "Solo los administradores de complejo pueden tener esta asignación."})

    def save(self, *args, **kwargs):
        # El acceso al panel acompaña al rol; no convierte al usuario en superusuario.
        if not self.is_superuser:
            self.is_staff = self.rol == "ADMIN_PLATAFORMA" or (
                self.rol == "ADMIN_COMPLEJO" and self.complejo_id is not None
            )
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {"is_staff"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.email}"
