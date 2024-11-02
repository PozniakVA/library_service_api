from rest_framework import generics
from rest_framework.permissions import AllowAny

from users_service.serializer import UserSerializer, UserMeSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserMeSerializer

    def get_object(self):
        return self.request.user
