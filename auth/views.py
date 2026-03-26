# api/auth_views.py
from django.contrib.auth import authenticate, login, logout
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .serializers import SignupSerializer, LoginSerializer
from api.serializers import UserSerializer
from rest_framework.settings import api_settings
from rest_framework.authentication import BasicAuthentication, SessionAuthentication

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
    # CRITICAL: This prevents the 'Session/CSRF' check that forces the 403
    authentication_classes = [BasicAuthentication, SessionAuthentication] 
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        # 1. This triggers the validate() in Serializer.
        # - 401 if authenticate fails
        # - 403 if user.is_active is False
        # - 400 if fields are missing
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        
        # 2. If it reaches here, the user is valid and active
        user = serializer.validated_data["user"]
        
        # Handles the session login for the request
        login(request, user)

        user_data = UserSerializer(user).data
        
        return Response({
            "message": "Login successfully", 
            "user_data": user_data 
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        response = Response({"message": "Logout successfully"}, status=status.HTTP_200_OK)

        # Explicitly Clear Cookies
        response.delete_cookie('sessionid')
        response.delete_cookie('csrftoken') 
        
        return response




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


