from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer) :
    password = serializers.CharField(write_only = True)
    password2 = serializers.CharField(write_only = True)

    class Meta :
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'profile_picture',
            'password',
            'password2',
        ]

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2'] :
            raise serializers.ValidationError('Passwords do not match.')
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class VerifyEmailSerializer(serializers.Serializer) :
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class ResendOTPSerializer(serializers.Serializer) :
    email = serializers.EmailField()

class PasswordResetRequestSerializer(serializers.Serializer) :
    email = serializers.EmailField()

class PasswordResetVerifySerializer(serializers.Serializer) : 
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError(
                {"new_password": "Passwords do not match."}
            )

        return attrs

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]

        user = authenticate(
            email=email,
            password=password
        )

        if user is None:
            raise serializers.ValidationError(
                {"error": "Invalid email or password."}
            )

        if not user.is_verified:
            raise serializers.ValidationError(
                {"error": "Please verify your email before logging in."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"error": "This account is inactive."}
            )

        refresh = RefreshToken.for_user(user)

        attrs["user"] = user
        attrs["refresh"] = str(refresh)
        attrs["access"] = str(refresh.access_token)

        return attrs

class UserProfileSerializer(serializers.ModelSerializer) :

    class Meta :
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'profile_picture'
        ]
        read_only_fields = ['email']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "first_name", "last_name","profile_picture"]

class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=True)