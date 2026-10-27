from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get(username=response.data["username"])
        refresh = RefreshToken.for_user(user)
        response.data = {"user": UserSerializer(user).data, "access": str(refresh.access_token), "refresh": str(refresh)}
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
