# api/auth_views.py
from django.contrib.auth import authenticate, login, logout
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .serializers import SignupSerializer, LoginSerializer


# For CSRF
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token



class SignupView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SignupSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "Signup successfully", "id": str(user.id)},
            status=status.HTTP_200_OK,
        )

class LoginView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        return Response({"message": "Login successfully"}, status=status.HTTP_200_OK)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Logout successfully"}, status=status.HTTP_200_OK)




@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


# # not yet used 
# class PasswordResetView(GenericAPIView):
#     permission_classes = [permissions.AllowAny]
#     serializer_class = PasswordResetSerializer

#     def post(self, request):
#         serializer = self.get_serializer(data=request.data, context={"request": request})
#         serializer.is_valid(raise_exception=True)
#         serializer.save(request=request)
#         return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)


