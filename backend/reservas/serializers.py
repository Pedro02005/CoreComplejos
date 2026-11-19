from rest_framework import serializers

from complejos.models import Cancha


from .models import (
    Recomendacion,
    AsignacionPromocion
)


from .models import Reserva, DetallePrecio, HistorialReserva, Encuesta, RespuestaEncuesta


class ConsultaDisponibilidadSerializer(serializers.Serializer):

    fecha = serializers.DateField()

    duracion = serializers.IntegerField(
        min_value=60,
        max_value=180
    )

    def validate_duracion(self, value):
        if value % 30 != 0:
            raise serializers.ValidationError(
                "La duración debe ser múltiplo de 30."
            )

        return value


class CotizacionSerializer(serializers.Serializer):

    cancha_id = serializers.PrimaryKeyRelatedField(
        queryset=Cancha.objects.all(),
        source="cancha"
    )

    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()


    asignacion_id = serializers.IntegerField(
        required=False,
        min_value=1
    )


    def validate(self, attrs):
        if attrs["inicio"] >= attrs["fin"]:
            raise serializers.ValidationError(
                "El inicio debe ser anterior al fin."
            )

        return attrs
    

class CancelarReservaSerializer(serializers.Serializer):

    motivo = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        trim_whitespace=True
    )


class DetallePrecioSerializer(serializers.ModelSerializer):

    class Meta:
        model = DetallePrecio

        fields = (
            "id",
            "tarifa",
            "inicio",
            "fin",
            "valor_hora",
            "subtotal",
        )

        read_only_fields = fields


class HistorialReservaSerializer(serializers.ModelSerializer):

    actor = serializers.CharField(
        source="actor.username",
        read_only=True
    )

    class Meta:
        model = HistorialReserva

        fields = (
            "id",
            "evento",
            "actor",
            "estado_anterior",
            "estado_nuevo",
            "motivo",
            "fecha",
        )

        read_only_fields = fields


class ReservaListadoSerializer(serializers.ModelSerializer):

    cliente = serializers.CharField(
        source="cliente.username",
        read_only=True
    )

    cancha = serializers.CharField(
        source="cancha.nombre",
        read_only=True
    )

    complejo = serializers.CharField(
        source="cancha.complejo.nombre",
        read_only=True
    )

    class Meta:
        model = Reserva

        fields = (
            "id",
            "cliente",
            "complejo",
            "cancha",
            "inicio",
            "fin",
            "estado",
            "total",
            "cancelable_hasta",
        )

        read_only_fields = fields


class ReservaDetalleSerializer(ReservaListadoSerializer):

    detalles_precio = DetallePrecioSerializer(
        many=True,
        read_only=True
    )

    historial = HistorialReservaSerializer(
        many=True,
        read_only=True
    )

    class Meta(ReservaListadoSerializer.Meta):

        fields = ReservaListadoSerializer.Meta.fields + (
            "detalles_precio",
            "historial",
        )

        read_only_fields = fields


class EncuestaPendienteSerializer(serializers.ModelSerializer):

    reserva_id = serializers.IntegerField(
        read_only=True
    )

    complejo = serializers.CharField(
        source="reserva.cancha.complejo.nombre",
        read_only=True
    )

    cancha = serializers.CharField(
        source="reserva.cancha.nombre",
        read_only=True
    )

    inicio = serializers.DateTimeField(
        source="reserva.inicio",
        read_only=True
    )

    fin = serializers.DateTimeField(
        source="reserva.fin",
        read_only=True
    )

    class Meta:
        model = Encuesta

        fields = (
            "id",
            "reserva_id",
            "tipo",
            "complejo",
            "cancha",
            "inicio",
            "fin",
            "fecha_creacion",
        )

        read_only_fields = fields



class ResponderEncuestaSerializer(serializers.Serializer):

    # Campos de cancelación
    motivo_cancelacion = serializers.ChoiceField(
        choices=RespuestaEncuesta.MOTIVOS_CANCELACION,
        required=False
    )

    hubiera_evitado = serializers.ChoiceField(
        choices=RespuestaEncuesta.SOLUCIONES_CANCELACION,
        required=False
    )

    # Campos de experiencia
    calificacion = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False
    )

    volveria_reservar = serializers.BooleanField(
        required=False
    )

    aspecto_mejorar = serializers.ChoiceField(
        choices=RespuestaEncuesta.ASPECTOS_MEJORA,
        required=False
    )

    # Campo común
    comentario = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True
    )



class RespuestaEncuestaSerializer(serializers.ModelSerializer):

    class Meta:
        model = RespuestaEncuesta

        fields = (
            "id",
            "encuesta",
            "motivo_cancelacion",
            "hubiera_evitado",
            "calificacion",
            "volveria_reservar",
            "aspecto_mejorar",
            "comentario",
            "fecha_respuesta",
        )

        read_only_fields = fields



class RecomendacionClienteSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = Recomendacion

        fields = (
            "id",
            "regla",
            "categoria",
            "titulo",
            "motivo",
            "accion_sugerida",
            "prioridad",
            "fecha_creacion",
            "vence_en",
        )

        read_only_fields = fields



class MiPromocionSerializer(
    serializers.ModelSerializer
):

    codigo = serializers.CharField(
        source="promocion.codigo",
        read_only=True
    )

    nombre = serializers.CharField(
        source="promocion.nombre",
        read_only=True
    )

    descripcion = serializers.CharField(
        source="promocion.descripcion",
        read_only=True
    )

    tipo_descuento = serializers.CharField(
        source="promocion.tipo_descuento",
        read_only=True
    )

    valor_descuento = serializers.DecimalField(
        source="promocion.valor_descuento",
        max_digits=8,
        decimal_places=2,
        read_only=True
    )

    regla_objetivo = serializers.CharField(
        source="promocion.regla_objetivo",
        read_only=True
    )

    vence_en = serializers.DateTimeField(
        source="promocion.fecha_fin",
        read_only=True
    )

    class Meta:
        model = AsignacionPromocion

        fields = (
            "id",
            "promocion",
            "codigo",
            "nombre",
            "descripcion",
            "tipo_descuento",
            "valor_descuento",
            "regla_objetivo",
            "recomendacion",
            "motivo_asignacion",
            "estado",
            "fecha_asignacion",
            "vence_en",
            "fecha_uso",
            "reserva_utilizada",
            "descuento_aplicado",
        )

        read_only_fields = fields
