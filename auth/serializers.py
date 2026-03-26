from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
# from django.contrib.auth.forms import PasswordResetForm

from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework import serializers

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        trim_whitespace=False,
        style={"input_type": "password"},    
    )

    class Meta:
        model = User
        fields = ("id", "email", "name", "password")

    def validate_password(self, value):
        # runs Django’s default password validators
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, 
        trim_whitespace=False, 
        style={"input_type": "password"}
    )

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
           
            user = authenticate(request, username=email, password=password)

            if not user:
                # 401 Unauthorized: The "Who are you?" check
                raise AuthenticationFailed("Invalid credentials")
            
            if not user.is_active:
                # 403 Forbidden: The "Are you allowed?" check
                raise PermissionDenied("User account is deactivated")

            attrs["user"] = user
        else:
            # 400 Bad Request: The "Did you send data?" check
            raise serializers.ValidationError("Both email and password are required")

        return attrs


# class PasswordResetSerializer(serializers.Serializer):
#     email = serializers.EmailField()

#     def validate_email(self, value):
#         self._form = PasswordResetForm(data={"email": value})
#         if not self._form.is_valid():
#             raise serializers.ValidationError("Invalid email")
#         return value

#     def save(self, request):
#         self._form.save(request=request, use_https=request.is_secure())


