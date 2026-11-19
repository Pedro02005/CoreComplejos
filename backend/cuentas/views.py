from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import PerfilSerializer, RegistroSerializer


class RegistroView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RegistroSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(PerfilSerializer(usuario).data, status=201)


class PerfilView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PerfilSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        # La cuenta se obtiene del token, no de un identificador enviado por el cliente.
        return self.request.user
