from django.urls import path
from .views import (UserRegistrationView,VerifyEmailView,ResendOTPView,PasswordResetRequestView,
                    PasswordResetConfirmView,LoginView,LogoutView,UserProfileView,GoogleLoginView)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/',UserRegistrationView.as_view(),name='register'),
    path('google/',GoogleLoginView.as_view(),name="google-login"),
    path('verify-email/',VerifyEmailView.as_view(),name='verify-email'),
    path('login/',LoginView.as_view(), name='login'),
    path('logout/',LogoutView.as_view(), name='logout'),
    path('token/refresh/',TokenRefreshView.as_view(),name='token-refresh'),
    path('resend-otp/',ResendOTPView.as_view(),name='resend-otp'),
    path('password-reset/request/',PasswordResetRequestView.as_view(),name='password-reset-request'),
    path('password-reset/confirm/',PasswordResetConfirmView.as_view(),name='password-reset-confirm'),

    path('profile/',UserProfileView.as_view(),name='profile'),

]
