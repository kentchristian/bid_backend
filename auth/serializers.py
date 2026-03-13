from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import PasswordResetForm
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
        user = authenticate(request, email=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("User is inactive")
        attrs["user"] = user
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


