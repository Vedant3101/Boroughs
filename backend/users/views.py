from rest_framework import generics, permissions

from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — create a user and return JWT pair."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
