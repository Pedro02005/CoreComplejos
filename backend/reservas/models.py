from django.db import models
from django.conf import settings
from django.db.models import F, Q

from django.core.exceptions import ValidationError


from django.utils import timezone
from decimal import Decimal



class Reserva(models.Model):

    ESTADOS = [
        ("CONFIRMADA", "Confirmada"),
        ("CANCELADA", "Cancelada"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas"
    )

    cancha = models.ForeignKey(
        "complejos.Cancha",
        on_delete=models.PROTECT,
        related_name="reservas"
    )

    inicio = models.DateTimeField()
    fin = models.DateTimeField()

    estado = models.CharField(
        max_length=12,
        choices=ESTADOS,
        default="CONFIRMADA"
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    clave_solicitud = models.UUIDField(unique=True)

    cancelable_hasta = models.DateTimeField()

    class Meta:
        ordering = ["-inicio"]

        constraints = [
            models.CheckConstraint(
                condition=Q(inicio__lt=F("fin")),
                name="reserva_inicio_menor_fin"
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="reserva_total_no_negativo"
            ),
        ]

    def __str__(self):
        return f"Reserva {self.id} - {self.cancha}"
    
    def clean(self):
        super().clean()

        if not self.cancha_id or not self.inicio or not self.fin:
            return

        if self.inicio >= self.fin:
            raise ValidationError(
                "El inicio debe ser anterior al fin."
            )

        if self.estado == "CONFIRMADA":

            reservas = Reserva.objects.filter(
                cancha_id=self.cancha_id,
                estado="CONFIRMADA",
                inicio__lt=self.fin,
                fin__gt=self.inicio
            ).exclude(pk=self.pk)

            if reservas.exists():
                raise ValidationError(
                    "Ya existe una reserva confirmada "
                    "para esta cancha en ese horario."
                )
                

class HistorialReserva(models.Model):

    EVENTOS = [
        ("CREACION", "Creación"),
        ("CANCELACION", "Cancelación"),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name="historial"
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_reservas"
    )

    evento = models.CharField(
        max_length=15,
        choices=EVENTOS
    )

    estado_anterior = models.CharField(
        max_length=12,
        blank=True
    )

    estado_nuevo = models.CharField(
        max_length=12
    )

    motivo = models.TextField(
        blank=True
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["fecha", "pk"]
        verbose_name = "Historial de reserva"
        verbose_name_plural = "Historial de reservas"

    def __str__(self):
        return f"Reserva {self.reserva_id} - {self.get_evento_display()}"
    

class DetallePrecio(models.Model):

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name="detalles_precio"
    )

    tarifa = models.ForeignKey(
        "complejos.Tarifa",
        on_delete=models.PROTECT,
        related_name="detalles_reserva"
    )

    inicio = models.DateTimeField()
    fin = models.DateTimeField()

    valor_hora = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        ordering = ["inicio", "pk"]

        verbose_name = "Detalle de precio"
        verbose_name_plural = "Detalles de precio"

        constraints = [
            models.CheckConstraint(
                condition=Q(inicio__lt=F("fin")),
                name="detalle_precio_inicio_menor_fin"
            ),

            models.CheckConstraint(
                condition=Q(valor_hora__gt=0),
                name="detalle_precio_valor_hora_positivo"
            ),

            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="detalle_precio_subtotal_no_negativo"
            ),
        ]

    def clean(self):
        super().clean()

        if self.inicio and self.fin:
            if self.inicio >= self.fin:
                raise ValidationError(
                    "El inicio debe ser anterior al fin."
                )

        if self.reserva_id and self.tarifa_id:

            if self.reserva.cancha_id != self.tarifa.cancha_id:
                raise ValidationError(
                    "La tarifa no corresponde a la cancha reservada."
                )

            if self.inicio and self.fin:
                if (
                    self.inicio < self.reserva.inicio
                    or self.fin > self.reserva.fin
                ):
                    raise ValidationError(
                        "El detalle debe estar dentro del horario de la reserva."
                    )

    def __str__(self):
        return f"Reserva {self.reserva_id} - ${self.subtotal}"



class Encuesta(models.Model):

    TIPO_CANCELACION = "CANCELACION"
    TIPO_EXPERIENCIA = "EXPERIENCIA"

    TIPOS = [
        (TIPO_CANCELACION, "Encuesta de cancelación"),
        (TIPO_EXPERIENCIA, "Encuesta de experiencia"),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name="encuestas"
    )

    tipo = models.CharField(
        max_length=15,
        choices=TIPOS
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-fecha_creacion"]

        verbose_name = "Encuesta"
        verbose_name_plural = "Encuestas"

        constraints = [
            models.UniqueConstraint(
                fields=["reserva", "tipo"],
                name="encuesta_unica_por_reserva_tipo"
            )
        ]

    def clean(self):
        super().clean()

        if not self.reserva_id:
            return

        reserva = self.reserva

        if self.tipo == self.TIPO_CANCELACION:

            if reserva.estado != "CANCELADA":
                raise ValidationError(
                    "La encuesta de cancelación requiere "
                    "una reserva cancelada."
                )

        elif self.tipo == self.TIPO_EXPERIENCIA:

            if reserva.estado != "CONFIRMADA":
                raise ValidationError(
                    "La encuesta de experiencia requiere "
                    "una reserva confirmada."
                )

            if timezone.now() < reserva.fin:
                raise ValidationError(
                    "La encuesta de experiencia solo "
                    "se permite después del horario reservado."
                )

    def __str__(self):
        return (
            f"Encuesta {self.id} - "
            f"Reserva {self.reserva_id} - "
            f"{self.get_tipo_display()}"
        )



class RespuestaEncuesta(models.Model):

    MOTIVOS_CANCELACION = [
        ("PRECIO", "Precio elevado"),
        ("HORARIO", "Problemas de horario"),
        ("UBICACION", "Ubicación"),
        ("CAMBIO_PLANES", "Cambio de planes"),
        ("INSTALACIONES", "Problemas de instalaciones"),
        ("OTRO", "Otro motivo"),
    ]

    SOLUCIONES_CANCELACION = [
        ("DESCUENTO", "Un descuento"),
        ("CAMBIO_HORARIO", "Otro horario"),
        ("OTRA_CANCHA", "Otra cancha o complejo"),
        ("MEJORES_INSTALACIONES", "Mejores instalaciones"),
        ("NADA", "Nada hubiera evitado cancelar"),
        ("OTRO", "Otra solución"),
    ]

    ASPECTOS_MEJORA = [
        ("PRECIO", "Precio"),
        ("INSTALACIONES", "Instalaciones"),
        ("ATENCION", "Atención al cliente"),
        ("DISPONIBILIDAD", "Disponibilidad de horarios"),
        ("NINGUNO", "Ninguno"),
        ("OTRO", "Otro aspecto"),
    ]

    encuesta = models.OneToOneField(
        Encuesta,
        on_delete=models.PROTECT,
        related_name="respuesta"
    )

    # Campos de cancelación
    motivo_cancelacion = models.CharField(
        max_length=20,
        choices=MOTIVOS_CANCELACION,
        blank=True
    )

    hubiera_evitado = models.CharField(
        max_length=25,
        choices=SOLUCIONES_CANCELACION,
        blank=True
    )

    # Campos de experiencia
    calificacion = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    volveria_reservar = models.BooleanField(
        null=True,
        blank=True
    )

    aspecto_mejorar = models.CharField(
        max_length=20,
        choices=ASPECTOS_MEJORA,
        blank=True
    )

    # Campos comunes
    comentario = models.TextField(
        max_length=1000,
        blank=True
    )

    fecha_respuesta = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        verbose_name = "Respuesta de encuesta"
        verbose_name_plural = "Respuestas de encuestas"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(calificacion__isnull=True)
                    | Q(calificacion__gte=1, calificacion__lte=5)
                ),
                name="respuesta_calificacion_1_a_5"
            )
        ]

    def clean(self):
        super().clean()

        if not self.encuesta_id:
            return

        tipo = self.encuesta.tipo

        self.comentario = (self.comentario or "").strip()

        if tipo == Encuesta.TIPO_CANCELACION:

            if not self.motivo_cancelacion:
                raise ValidationError({
                    "motivo_cancelacion": "Indica el motivo de cancelación."
                })

            if not self.hubiera_evitado:
                raise ValidationError({
                    "hubiera_evitado": "Indica qué habría evitado cancelar."
                })

            if (
                self.calificacion is not None
                or self.volveria_reservar is not None
                or self.aspecto_mejorar
            ):
                raise ValidationError(
                    "Una encuesta de cancelación no puede "
                    "contener respuestas de experiencia."
                )

        elif tipo == Encuesta.TIPO_EXPERIENCIA:

            if self.calificacion is None:
                raise ValidationError({
                    "calificacion": "La calificación es obligatoria."
                })

            if not 1 <= self.calificacion <= 5:
                raise ValidationError({
                    "calificacion": "La calificación debe ser de 1 a 5."
                })

            if self.volveria_reservar is None:
                raise ValidationError({
                    "volveria_reservar": "Debes indicar si volverías."
                })

            if self.motivo_cancelacion or self.hubiera_evitado:
                raise ValidationError(
                    "Una encuesta de experiencia no puede "
                    "contener respuestas de cancelación."
                )

    def __str__(self):
        return f"Respuesta de encuesta {self.encuesta_id}"



class Recomendacion(models.Model):

    REGLAS = [
        ("R01", "Problema de precio"),
        ("R02", "Problema de horario"),
        ("R03", "Problema de ubicación"),
        ("R04", "Mala experiencia"),
        ("R05", "Fidelización"),
        ("R06", "Cancelaciones recurrentes"),
        ("R07", "Recomendación general"),
    ]

    CATEGORIAS = [
        ("PRECIO", "Precio"),
        ("HORARIO", "Horario"),
        ("UBICACION", "Ubicación"),
        ("EXPERIENCIA", "Experiencia"),
        ("FIDELIZACION", "Fidelización"),
        ("CANCELACION", "Cancelaciones"),
        ("GENERAL", "General"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recomendaciones"
    )

    regla = models.CharField(
        max_length=3,
        choices=REGLAS
    )

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS
    )

    titulo = models.CharField(
        max_length=150
    )

    motivo = models.TextField()

    accion_sugerida = models.CharField(
        max_length=50
    )

    prioridad = models.PositiveSmallIntegerField()

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    vence_en = models.DateTimeField()

    activa = models.BooleanField(
        default=True
    )

    class Meta:

        ordering = ["-fecha_creacion", "-id"]

        verbose_name = "Recomendación"
        verbose_name_plural = "Recomendaciones"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(prioridad__gte=1)
                    & Q(prioridad__lte=4)
                ),
                name="recomendacion_prioridad_1_a_4"
            )
        ]

    def clean(self):
        super().clean()

        errores = {}

        # Validar campos de texto
        for campo in (
            "titulo",
            "motivo",
            "accion_sugerida"
        ):
            valor = getattr(self, campo, "")

            if isinstance(valor, str):
                valor = valor.strip()
                setattr(self, campo, valor)

                if not valor:
                    errores[campo] = (
                        "Este campo no puede estar vacío."
                    )

        # Validar prioridad
        if self.prioridad is not None:
            if not 1 <= self.prioridad <= 4:
                errores["prioridad"] = (
                    "La prioridad debe estar entre 1 y 4."
                )

        # Validar caducidad
        if self.vence_en:

            if timezone.is_naive(self.vence_en):
                errores["vence_en"] = (
                    "La fecha debe incluir zona horaria."
                )

            elif (
                self._state.adding
                and self.vence_en <= timezone.now()
            ):
                errores["vence_en"] = (
                    "La fecha de vencimiento debe ser futura."
                )

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return (
            f"Recomendación {self.pk} - "
            f"{self.regla} - {self.cliente}"
        )


class EjecucionRegla(models.Model):

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ejecuciones_reglas"
    )

    regla = models.CharField(
        max_length=3,
        choices=Recomendacion.REGLAS
    )

    cumplida = models.BooleanField(
        default=False
    )

    detalle = models.TextField()

    recomendacion = models.ForeignKey(
        Recomendacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ejecuciones"
    )

    fecha_ejecucion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-fecha_ejecucion", "-id"]

        verbose_name = "Ejecución de regla"
        verbose_name_plural = "Ejecuciones de reglas"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        cumplida=True,
                        recomendacion__isnull=False
                    )
                    | Q(
                        cumplida=False,
                        recomendacion__isnull=True
                    )
                ),
                name="ejecucion_regla_resultado_coherente"
            )
        ]

    def clean(self):
        super().clean()

        errores = {}

        # Explicación obligatoria
        self.detalle = (self.detalle or "").strip()

        if not self.detalle:
            errores["detalle"] = (
                "Debes indicar el resultado de la regla."
            )

        # Regla cumplida: debe vincular recomendación
        if self.cumplida and not self.recomendacion_id:
            errores["recomendacion"] = (
                "Una regla cumplida debe tener "
                "una recomendación asociada."
            )

        # Regla no cumplida: no genera recomendación
        if not self.cumplida and self.recomendacion_id:
            errores["recomendacion"] = (
                "Una regla no cumplida no puede "
                "tener recomendación."
            )

        # Validar integridad de las relaciones
        if self.recomendacion_id:

            recomendacion = self.recomendacion

            if recomendacion.cliente_id != self.cliente_id:
                errores["recomendacion"] = (
                    "La recomendación pertenece "
                    "a otro cliente."
                )

            elif recomendacion.regla != self.regla:
                errores["recomendacion"] = (
                    "La regla no coincide con "
                    "la recomendación."
                )

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        resultado = (
            "Cumplida" if self.cumplida
            else "No cumplida"
        )

        return f"{self.regla} - {resultado}"


class Promocion(models.Model):

    TIPOS_DESCUENTO = [
        ("PORCENTAJE", "Porcentaje"),
        ("MONTO_FIJO", "Monto fijo"),
    ]


    
    
    REGLAS_OBJETIVO = [
        ("R01", "Precio elevado"),
        ("R05", "Fidelización"),
    ]


    regla_objetivo = models.CharField(
        max_length=3,
        choices=REGLAS_OBJETIVO,
        blank=True,
        default=""
    )

    
    nombre = models.CharField(
        max_length=150
    )

    codigo = models.CharField(
        max_length=30,
        unique=True
    )

    descripcion = models.TextField(
        blank=True
    )

    tipo_descuento = models.CharField(
        max_length=15,
        choices=TIPOS_DESCUENTO
    )

    valor_descuento = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    fecha_inicio = models.DateTimeField()

    fecha_fin = models.DateTimeField()

    limite_usos = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    activa = models.BooleanField(
        default=True
    )

    class Meta:

        ordering = ["-fecha_inicio", "-id"]

        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"

        constraints = [
            models.CheckConstraint(
                condition=Q(valor_descuento__gt=0),
                name="promocion_descuento_positivo"
            ),

            models.CheckConstraint(
                condition=(
                    Q(tipo_descuento="MONTO_FIJO")
                    | Q(
                        tipo_descuento="PORCENTAJE",
                        valor_descuento__lte=100
                    )
                ),
                name="promocion_porcentaje_maximo_100"
            ),

            models.CheckConstraint(
                condition=Q(
                    fecha_inicio__lt=F("fecha_fin")
                ),
                name="promocion_fechas_validas"
            ),

            models.CheckConstraint(
                condition=(
                    Q(limite_usos__isnull=True)
                    | Q(limite_usos__gte=1)
                ),
                name="promocion_limite_positivo"
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        self.nombre = (self.nombre or "").strip()
        self.codigo = (self.codigo or "").strip().upper()

        if not self.nombre:
            errores["nombre"] = "El nombre es obligatorio."

        if not self.codigo:
            errores["codigo"] = "El código es obligatorio."

        # Validar el descuento
        if self.valor_descuento is not None:

            if self.valor_descuento <= Decimal("0"):
                errores["valor_descuento"] = (
                    "El descuento debe ser positivo."
                )

            elif (
                self.tipo_descuento == "PORCENTAJE"
                and self.valor_descuento > Decimal("100")
            ):
                errores["valor_descuento"] = (
                    "El porcentaje no puede superar el 100%."
                )

        # Validar el período
        if self.fecha_inicio and self.fecha_fin:

            if (
                timezone.is_naive(self.fecha_inicio)
                or timezone.is_naive(self.fecha_fin)
            ):
                errores["fecha_inicio"] = (
                    "Las fechas deben incluir zona horaria."
                )

            elif self.fecha_inicio >= self.fecha_fin:
                errores["fecha_fin"] = (
                    "La fecha final debe ser posterior "
                    "a la fecha inicial."
                )

        # Validar el límite de usos
        if (
            self.limite_usos is not None
            and self.limite_usos < 1
        ):
            errores["limite_usos"] = (
                "El límite debe ser al menos 1."
            )

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"



class AsignacionPromocion(models.Model):

    ESTADOS = [
        ("DISPONIBLE", "Disponible"),
        ("UTILIZADA", "Utilizada"),
        ("REVOCADA", "Revocada"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="promociones_asignadas"
    )

    promocion = models.ForeignKey(
        Promocion,
        on_delete=models.PROTECT,
        related_name="asignaciones"
    )

    recomendacion = models.ForeignKey(
        Recomendacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promociones_asignadas"
    )

    motivo_asignacion = models.TextField(
        blank=True
    )

    estado = models.CharField(
        max_length=12,
        choices=ESTADOS,
        default="DISPONIBLE"
    )

    fecha_asignacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_uso = models.DateTimeField(
        null=True,
        blank=True
    )

    reserva_utilizada = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promociones_utilizadas"
    )

    descuento_aplicado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    class Meta:

        ordering = ["-fecha_asignacion", "-id"]

        verbose_name = "Asignación de promoción"
        verbose_name_plural = "Asignaciones de promociones"

        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "promocion"],
                name="promocion_unica_por_cliente"
            ),

            models.CheckConstraint(
                condition=(
                    Q(
                        estado="UTILIZADA",
                        reserva_utilizada__isnull=False,
                        fecha_uso__isnull=False,
                        descuento_aplicado__gt=0
                    )
                    | Q(
                        estado__in=["DISPONIBLE", "REVOCADA"],
                        reserva_utilizada__isnull=True,
                        fecha_uso__isnull=True,
                        descuento_aplicado=0
                    )
                ),
                name="asignacion_promocion_uso_coherente"
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        self.motivo_asignacion = (
            self.motivo_asignacion or ""
        ).strip()

        # 1. Debe tener justificación
        if (
            not self.recomendacion_id
            and not self.motivo_asignacion
        ):
            errores["motivo_asignacion"] = (
                "Indica un motivo o vincula "
                "una recomendación."
            )

        # 2. Verificar la recomendación
        if self.recomendacion_id:

            if (
                self.recomendacion.cliente_id
                != self.cliente_id
            ):
                errores["recomendacion"] = (
                    "La recomendación pertenece "
                    "a otro cliente."
                )

        # 3. Comprobar la promoción al asignarla
        if self.promocion_id and self._state.adding:

            promocion = self.promocion

            if not promocion.activa:
                errores["promocion"] = (
                    "No puedes asignar una promoción inactiva."
                )

            elif promocion.fecha_fin <= timezone.now():
                errores["promocion"] = (
                    "La promoción ya venció."
                )

        # 4. Verificar el uso de la promoción
        if self.estado == "UTILIZADA":

            if not self.reserva_utilizada_id:
                errores["reserva_utilizada"] = (
                    "Indica la reserva donde se utilizó."
                )

            elif (
                self.reserva_utilizada.cliente_id
                != self.cliente_id
            ):
                errores["reserva_utilizada"] = (
                    "La reserva pertenece a otro cliente."
                )

            if not self.fecha_uso:
                errores["fecha_uso"] = (
                    "Indica cuándo se utilizó."
                )

            if self.descuento_aplicado <= 0:
                errores["descuento_aplicado"] = (
                    "El descuento aplicado debe ser positivo."
                )

        else:

            if (
                self.reserva_utilizada_id
                or self.fecha_uso
                or self.descuento_aplicado != 0
            ):
                errores["estado"] = (
                    "Una promoción no utilizada no puede "
                    "tener datos de uso."
                )

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return (
            f"{self.promocion.codigo} - "
            f"{self.cliente} - {self.estado}"
        )
