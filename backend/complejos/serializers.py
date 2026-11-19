from rest_framework import serializers

from .models import Cancha, Complejo, HorarioAtencion, Tarifa


class FiltrosComplejoSerializer(serializers.Serializer):
    ciudad = serializers.CharField(required=False, max_length=100)
    nombre = serializers.CharField(required=False, max_length=100)


class FiltrosCanchaSerializer(FiltrosComplejoSerializer):
    complejo_id = serializers.IntegerField(required=False, min_value=1)
    deporte = serializers.ChoiceField(required=False, choices=Cancha.DEPORTES)


class ComplejoListadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complejo
        fields = ("id", "nombre", "descripcion", "ciudad", "direccion")
        read_only_fields = fields


class CanchaListadoSerializer(serializers.ModelSerializer):
    complejo_nombre = serializers.CharField(source="complejo.nombre", read_only=True)
    ciudad = serializers.CharField(source="complejo.ciudad", read_only=True)

    class Meta:
        model = Cancha
        fields = (
            "id", "nombre", "deporte", "capacidad",
            "complejo", "complejo_nombre", "ciudad",
        )
        read_only_fields = fields


class ComplejoDetalleSerializer(ComplejoListadoSerializer):
    canchas = CanchaListadoSerializer(source="canchas_activas", many=True, read_only=True)

    class Meta(ComplejoListadoSerializer.Meta):
        fields = ComplejoListadoSerializer.Meta.fields + ("canchas",)
        read_only_fields = fields


class HorarioAtencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioAtencion
        fields = ("id", "dia_semana", "apertura", "cierre")
        read_only_fields = fields


class TarifaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarifa
        fields = ("id", "dia_semana", "inicio", "fin", "valor_hora")
        read_only_fields = fields


class CanchaDetalleSerializer(CanchaListadoSerializer):
    horarios = HorarioAtencionSerializer(many=True, read_only=True)
    tarifas = TarifaSerializer(source="tarifas_activas", many=True, read_only=True)

    class Meta(CanchaListadoSerializer.Meta):
        fields = CanchaListadoSerializer.Meta.fields + ("horarios", "tarifas")
        read_only_fields = fields
