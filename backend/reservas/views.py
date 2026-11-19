from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Django
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.utils import timezone
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    PermissionDenied as DjangoPermissionDenied,
)

# Django REST Framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied as DRFPermissionDenied,
)

# Modelos
from complejos.models import Cancha, HorarioAtencion
from .models import (
    Reserva,
    Encuesta,
    Recomendacion,
    AsignacionPromocion,
)

# Serializadores
from .serializers import (
    ConsultaDisponibilidadSerializer,
    CotizacionSerializer,
    CancelarReservaSerializer,
    ReservaListadoSerializer,
    ReservaDetalleSerializer,
    EncuestaPendienteSerializer,
    ResponderEncuestaSerializer,
    RespuestaEncuestaSerializer,
    RecomendacionClienteSerializer,
    MiPromocionSerializer,
)

# Servicios del core
from .services.disponibilidad import verificar_disponibilidad
from .services.cotizacion import cotizar_reserva
from .services.reserva import confirmar_reserva
from .services.cancelacion import cancelar_reserva

# Servicios de encuestas
from .services.encuestas import (
    obtener_encuestas_pendientes,
    responder_encuesta,
)

# Servicios de promociones
from .services.promociones_reserva import (
    cotizar_reserva_con_promocion,
    confirmar_reserva_con_promocion,
)

# Servicios de recomendaciones personalizadas
from .services.asignacion_promociones import (
    asignar_promociones_personalizadas,
)



ZONA = ZoneInfo("America/Guayaquil")


class DisponibilidadView(APIView):

    def get(self, request, cancha_id):

        cancha = get_object_or_404(
            Cancha,
            id=cancha_id
        )

        serializer = ConsultaDisponibilidadSerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        fecha = serializer.validated_data["fecha"]
        duracion = serializer.validated_data["duracion"]

        dia = fecha.weekday()

        horarios = HorarioAtencion.objects.filter(
            cancha=cancha,
            dia_semana=dia
        ).order_by("apertura")

        opciones = []

        for horario in horarios:

            inicio = datetime.combine(
                fecha,
                horario.apertura,
                tzinfo=ZONA
            )

            cierre = datetime.combine(
                fecha,
                horario.cierre,
                tzinfo=ZONA
            )

            # Alinear al siguiente minuto 00 o 30.
            if inicio.minute not in (0, 30) or inicio.second:
                minutos = (
                    (30 - inicio.minute % 30) % 30
                )

                inicio = inicio.replace(
                    second=0,
                    microsecond=0
                )

                if minutos == 0:
                    minutos = 30

                inicio += timedelta(minutes=minutos)

            while inicio + timedelta(minutes=duracion) <= cierre:

                fin = inicio + timedelta(minutes=duracion)

                try:
                    disponible, motivo = verificar_disponibilidad(
                        cancha,
                        inicio,
                        fin
                    )

                    if disponible:
                        # No ofrecer intervalos sin cobertura tarifaria.
                        cotizacion = cotizar_reserva(
                            cancha,
                            inicio,
                            fin
                        )

                        opciones.append({
                            "inicio": inicio.isoformat(),
                            "fin": fin.isoformat(),
                            "total": cotizacion["total"],
                            "moneda": "USD"
                        })

                except ValidationError:
                    pass

                inicio += timedelta(minutes=30)

        return Response({
            "cancha": cancha.nombre,
            "fecha": fecha,
            "duracion": duracion,
            "opciones": opciones
        })



class CotizarView(APIView):

    def post(self, request):

        serializer = CotizacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        datos = serializer.validated_data

        try:
            cotizacion = cotizar_reserva_con_promocion(
                cancha=datos["cancha"],
                inicio=datos["inicio"],
                fin=datos["fin"],
                cliente=request.user,
                asignacion_id=datos.get("asignacion_id")
            )

        except DjangoValidationError as error:
            detalle = (
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

            raise ValidationError(detalle)

        return Response(cotizacion)

    
    
class ConfirmarReservaView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # 1. Consultar las reservas
        reservas = Reserva.objects.select_related(
            "cliente",
            "cancha__complejo"
        )

        # 2. Filtrar según el usuario
        if not request.user.is_superuser:
            reservas = reservas.filter(
                cliente=request.user
            )

        # 3. Convertir los objetos a JSON
        serializer = ReservaListadoSerializer(
            reservas,
            many=True
        )

        # 4. Devolver la respuesta
        return Response(serializer.data)

    def post(self, request):

        serializer = CotizacionSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        datos = serializer.validated_data

        try:

            reserva = confirmar_reserva_con_promocion(
                cliente=request.user,
                cancha=datos["cancha"],
                inicio=datos["inicio"],
                fin=datos["fin"],
                asignacion_id=datos.get("asignacion_id")
            )
       

        except DjangoValidationError as error:
            detalle = (
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

            raise ValidationError(detalle)

        return Response(
            {
                "id": reserva.id,
                "cliente": reserva.cliente.username,
                "cancha": reserva.cancha.nombre,
                "inicio": reserva.inicio,
                "fin": reserva.fin,
                "estado": reserva.estado,
                "total": str(reserva.total),
                "cancelable_hasta": reserva.cancelable_hasta
            },
            status=201
        )
        

class CancelarReservaView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, reserva_id):

        # 1. Validar los datos recibidos
        serializer = CancelarReservaSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        motivo = serializer.validated_data.get(
            "motivo", ""
        )

        # 2. Buscar la reserva
        reservas = Reserva.objects.all()

        # Los clientes solo pueden acceder a sus reservas
        if not request.user.is_superuser:
            reservas = reservas.filter(
                cliente=request.user
            )

        reserva = get_object_or_404(
            reservas,
            pk=reserva_id
        )

        # 3. Ejecutar la lógica de cancelación
        try:

            cancelar_reserva(
                reserva=reserva,
                actor=request.user,
                motivo=motivo
            )

        except DjangoValidationError as error:
            raise ValidationError(error.messages)

        except DjangoPermissionDenied as error:
            raise DRFPermissionDenied(str(error))

        # 4. Responder al cliente
        return Response(
            {
                "mensaje": "Reserva cancelada correctamente.",
                "id": reserva.id,
                "estado": reserva.estado,
                "motivo": motivo
            },
            status=200
        )


class ReservaDetalleView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, reserva_id):

        # 1. Consultar reservas y relaciones
        reservas = Reserva.objects.select_related(
            "cliente",
            "cancha__complejo"
        ).prefetch_related(
            "detalles_precio",
            "historial__actor"
        )

        # 2. Aplicar permisos
        if not request.user.is_superuser:
            reservas = reservas.filter(
                cliente=request.user
            )

        # 3. Buscar la reserva solicitada
        reserva = get_object_or_404(
            reservas,
            pk=reserva_id
        )

        # 4. Serializar toda la información
        serializer = ReservaDetalleSerializer(
            reserva
        )

        return Response(serializer.data)



class EncuestasPendientesView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # 1. Obtener encuestas del usuario autenticado
        encuestas = obtener_encuestas_pendientes(
            cliente=request.user
        )

        # 2. Convertir las encuestas a JSON
        serializer = EncuestaPendienteSerializer(
            encuestas,
            many=True
        )

        # 3. Devolver la respuesta
        return Response(serializer.data)



class ResponderEncuestaView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, encuesta_id):

        # 1. Validar los datos recibidos
        serializer = ResponderEncuestaSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        # 2. Buscar la encuesta del cliente
        encuesta = get_object_or_404(
            Encuesta.objects.select_related("reserva"),
            pk=encuesta_id,
            reserva__cliente=request.user
        )

        # 3. Ejecutar el servicio
        try:
            respuesta = responder_encuesta(
                encuesta=encuesta,
                cliente=request.user,
                datos=serializer.validated_data
            )

        except DjangoValidationError as error:

            detalle = (
                error.message_dict
                if hasattr(error, "message_dict")
                else error.messages
            )

            raise ValidationError(detalle)

        # 4. Serializar la respuesta guardada
        resultado = RespuestaEncuestaSerializer(
            respuesta
        )

        # 5. Devolver HTTP 201
        return Response(
            resultado.data,
            status=201
        )


class MisRecomendacionesView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        ahora = timezone.now()

        recomendaciones = Recomendacion.objects.filter(
            cliente=request.user,
            activa=True,
            vence_en__gt=ahora
        ).order_by(
            "prioridad",
            "-fecha_creacion",
            "-id"
        )

        serializer = RecomendacionClienteSerializer(
            recomendaciones,
            many=True
        )

        return Response({
            "cantidad": len(serializer.data),
            "recomendaciones": serializer.data
        })


class MisPromocionesView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        ahora = timezone.now()

        # 1. Consultar únicamente las asignaciones
        # del usuario autenticado
        asignaciones = (
            AsignacionPromocion.objects
            .filter(cliente=request.user)
            .select_related(
                "promocion",
                "recomendacion",
                "reserva_utilizada"
            )
        )

        # 2. Candidatas a estar disponibles
        candidatas = list(
            asignaciones.filter(
                estado="DISPONIBLE",
                promocion__activa=True,
                promocion__fecha_inicio__lte=ahora,
                promocion__fecha_fin__gt=ahora
            ).order_by(
                "-fecha_asignacion",
                "-id"
            )
        )

        # 3. Contar usos globales de esas campañas
        promocion_ids = [
            asignacion.promocion_id
            for asignacion in candidatas
        ]

        usos_por_promocion = {
            fila["promocion_id"]: fila["cantidad"]
            for fila in (
                AsignacionPromocion.objects.filter(
                    promocion_id__in=promocion_ids,
                    estado="UTILIZADA"
                ).values(
                    "promocion_id"
                ).annotate(
                    cantidad=Count("id")
                )
            )
        }

        # 4. Excluir promociones sin cupo
        disponibles = []

        for asignacion in candidatas:

            promocion = asignacion.promocion

            usos = usos_por_promocion.get(
                promocion.id,
                0
            )

            if (
                promocion.limite_usos is None
                or usos < promocion.limite_usos
            ):
                disponibles.append(asignacion)

        # 5. Consultar las promociones utilizadas
        utilizadas = list(
            asignaciones.filter(
                estado="UTILIZADA"
            ).order_by(
                "-fecha_uso",
                "-id"
            )
        )

        # 6. Serializar
        serializer_disponibles = MiPromocionSerializer(
            disponibles,
            many=True
        )

        serializer_utilizadas = MiPromocionSerializer(
            utilizadas,
            many=True
        )

        return Response({
            "cantidad_disponibles": len(disponibles),
            "disponibles": serializer_disponibles.data,
            "cantidad_utilizadas": len(utilizadas),
            "utilizadas": serializer_utilizadas.data
        })



class ActualizarBeneficiosView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        resultado = asignar_promociones_personalizadas(
            cliente=request.user,
            dias=90
        )

        return Response({
            "mensaje": "Beneficios actualizados correctamente.",
            "promociones_nuevas": resultado["nuevas"],
            "cantidad_asignaciones": resultado[
                "cantidad_asignaciones"
            ],
            "reglas_sin_campana": resultado[
                "reglas_sin_campana"
            ]
        })
