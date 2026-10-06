import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from users.factories import UnverifiedUserFactory
from users.models import OTP
from .helpers import extract_otp

pytestmark = pytest.mark.django_db

REGISTER_URL = reverse('register')
VERIFY_URL = reverse('verify-email')
RESEND_URL = reverse('resend-otp')


def register_and_get_otp(api_client, email='otpuser@example.com'):
    """Goes through the real registration endpoint, then reads the OTP
    back out of the captured test email - a black-box way to get a VALID,
    correctly-hashed OTP without needing to know how otp_hash is computed."""
    api_client.post(REGISTER_URL, {
        'email': email, 'first_name': 'Otp', 'last_name': 'User',
        'password': 'StrongPass123!', 'password2': 'StrongPass123!',
    })
    return extract_otp(mail.outbox[-1])


def test_verify_email_success(api_client):
    email = 'verify1@example.com'
    otp_code = register_and_get_otp(api_client, email)

    response = api_client.post(VERIFY_URL, {'email': email, 'otp': otp_code})

    assert response.status_code == status.HTTP_200_OK

    from django.contrib.auth import get_user_model
    
    user = get_user_model().objects.get(email=email)
    assert user.is_verified is True


def test_verify_wrong_otp_returns_remaining_attempts(api_client):
    email = 'verify2@example.com'
    register_and_get_otp(api_client, email)

    response = api_client.post(VERIFY_URL, {'email': email, 'otp': '000000'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'remaining_attempts' in response.data


def test_verify_five_wrong_attempts_then_locked(api_client):
    email = 'verify3@example.com'
    register_and_get_otp(api_client, email)

    for _ in range(5):
        response = api_client.post(VERIFY_URL, {'email': email, 'otp': '000000'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # The 6th attempt (even with the right code) must give the distinct
    # "too many attempts" message, not the generic invalid-OTP one.
    locked_response = api_client.post(VERIFY_URL, {'email': email, 'otp': '000000'})
    assert locked_response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'remaining_attempts' not in locked_response.data
    assert 'too many attempts' in str(locked_response.data).lower()


def test_verify_expired_otp(api_client):
    email = 'verify4@example.com'
    otp_code = register_and_get_otp(api_client, email)

    # Force it into the past directly - there's no API action for this,
    # so touching the model here is correct, not a shortcut around the test.
    OTP.objects.filter(user__email=email).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    response = api_client.post(VERIFY_URL, {'email': email, 'otp': otp_code})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'expired' in str(response.data).lower()


def test_verify_used_otp_cannot_be_reused(api_client):
    email = 'verify5@example.com'
    otp_code = register_and_get_otp(api_client, email)

    first = api_client.post(VERIFY_URL, {'email': email, 'otp': otp_code})
    assert first.status_code == status.HTTP_200_OK

    second = api_client.post(VERIFY_URL, {'email': email, 'otp': otp_code})
    assert second.status_code == status.HTTP_400_BAD_REQUEST


def test_verify_missing_fields(api_client):
    response = api_client.post(VERIFY_URL, {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in response.data
    assert 'otp' in response.data


def test_resend_otp_success(api_client):
    email = 'resend1@example.com'
    api_client.post(REGISTER_URL, {
        'email': email, 'first_name': 'R', 'last_name': 'U',
        'password': 'StrongPass123!', 'password2': 'StrongPass123!',
    })
    mail.outbox.clear()

    response = api_client.post(RESEND_URL, {'email': email})

    assert response.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1


def test_resend_otp_already_verified(api_client):
    user = UnverifiedUserFactory(email='resend2@example.com')
    user.is_verified = True
    user.save(update_fields=['is_verified'])

    response = api_client.post(RESEND_URL, {'email': user.email})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_resend_otp_unknown_email(api_client):
    response = api_client.post(RESEND_URL, {'email': 'nobody@example.com'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
