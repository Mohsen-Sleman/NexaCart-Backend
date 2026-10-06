from rest_framework.generics import CreateAPIView,RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser,MultiPartParser,FormParser
from .services import verify_google_token
from .models import OTP,User
from .serializer import (UserRegistrationSerializer,VerifyEmailSerializer,ResendOTPSerializer,
                        PasswordResetRequestSerializer,PasswordResetConfirmSerializer,LoginSerializer,
                        UserProfileSerializer,UserSerializer,GoogleLoginSerializer)
from .services import create_otp,send_otp_email,verify_otp,reset_password,MAX_OTP_ATTEMPTS

class UserRegistrationView(CreateAPIView) :
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data = request.data,context={'request' : request})
        
        serializer.is_valid(raise_exception = True)
        user = serializer.save()

        otp = create_otp(user = user,purpose=OTP.Purpose.EMAIL_VERIFICATION)
        send_otp_email(user,otp,'registration')
        return Response(
            {
                'message' : 'Registration successful, Please verify your email.'
            }
        ,status=status.HTTP_201_CREATED)

class VerifyEmailView(CreateAPIView):
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        entered_otp = serializer.validated_data["otp"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_obj = (
            OTP.objects
            .filter(
                user=user,
                purpose=OTP.Purpose.EMAIL_VERIFICATION,
                used_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if otp_obj is None:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = verify_otp(otp_obj, entered_otp)

        if result == "invalid":
            remaining_attempts = MAX_OTP_ATTEMPTS - otp_obj.attempts

            return Response(
                {
                    "error": "Invalid OTP.",
                    "remaining_attempts": remaining_attempts,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if result == "max_attempts":
            return Response(
                {
                    "error": "Too many attempts. Please request a new OTP."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if result == "expired":
            return Response(
                {
                    "error": "OTP has expired. Please request a new OTP."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if result == "used":
            return Response(
                {
                    "error": "OTP has already been used."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK
        )


class ResendOTPView(CreateAPIView):
    serializer_class = ResendOTPSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_verified:
            return Response(
                {"error": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp = create_otp(
            user=user,
            purpose=OTP.Purpose.EMAIL_VERIFICATION
        )

        send_otp_email(user, otp,'registration')

        return Response(
            {"message": "A new verification code has been sent."},
            status=status.HTTP_200_OK
        )


class PasswordResetRequestView(CreateAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "message": (
                        "If an account with this email exists, "
                        "a password reset code has been sent."
                    )
                },
                status=status.HTTP_200_OK
            )

        otp = create_otp(
            user=user,
            purpose=OTP.Purpose.PASSWORD_RESET
        )
        send_otp_email(user, otp,'password_reset')

        return Response(
            {
                "message": (
                    "If an account with this email exists, "
                    "a password reset code has been sent."
                )
            },
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(CreateAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        entered_otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_obj = (
            OTP.objects
            .filter(
                user=user,
                purpose=OTP.Purpose.PASSWORD_RESET,
                used_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if otp_obj is None:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = verify_otp(otp_obj, entered_otp)

        if result == "invalid":
            remaining_attempts = MAX_OTP_ATTEMPTS - otp_obj.attempts

            return Response(
                {
                    "error": "Invalid OTP.",
                    "remaining_attempts": remaining_attempts,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if result == "max_attempts":
            return Response(
                {"error": "Too many attempts. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if result == "expired":
            return Response(
                {"error": "OTP has expired. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if result == "used":
            return Response(
                {"error": "OTP has already been used."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reset_password(user, new_password)

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK
        )

class LoginView(CreateAPIView) :
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response (
            {
                "access" : serializer.validated_data['access'],
                "refresh" : serializer.validated_data['refresh'],
            }
        ,status=status.HTTP_200_OK)


class LogoutView(CreateAPIView):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

        except Exception:
            return Response(
                {"error": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK
        )


class UserProfileView(RetrieveUpdateAPIView) :
    lookup_field = 'pk'
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser,MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user



class GoogleLoginView(APIView):
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_token = serializer.validated_data["access_token"]

        google_data = verify_google_token(access_token)
        if google_data is None:
            return Response(
                {"detail": "Invalid Google access token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = google_data["email"]
        user = User.objects.filter(email=email).first()

        is_new_user = False
        if user is None:
            user = User.objects.create(
                email=email,
                first_name=google_data.get("given_name", ""),
                last_name=google_data.get("family_name", ""),
                is_verified=True,
            )
            user.set_unusable_password()
            user.save()
            is_new_user = True
        else:
            if not user.is_verified:
                user.is_verified = True
                user.save(update_fields=["is_verified"])
                
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_new_user": is_new_user,
            "user": UserSerializer(user).data,  
        }, status=status.HTTP_200_OK)