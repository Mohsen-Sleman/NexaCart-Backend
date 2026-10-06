import pytest
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from users.factories import UserFactory, DEFAULT_PASSWORD
from users.models import OTP, User
from .helpers import extract_otp

pytestmark = pytest.mark.django_db

REQUEST_URL = reverse('password-reset-request')
CONFIRM_URL = reverse('password-reset-confirm')

NEW_PASSWORD = 'BrandNewPass456!'


def request_and_get_otp(api_client, email):
    mail.outbox.clear()
    response = api_client.post(REQUEST_URL, {'email': email})
    assert response.status_code == status.HTTP_200_OK
    return extract_otp(mail.outbox[-1])


def test_request_reset_sends_email(api_client):
    user = UserFactory(email='reset1@example.com')
    otp_code = request_and_get_otp(api_client, user.email)
    assert len(otp_code) == 6


def test_request_reset_unknown_email(api_client):
    mail.outbox.clear()
    api_client.post(REQUEST_URL, {'email': 'nobody@example.com'})
    assert len(mail.outbox) == 0


def test_confirm_success_changes_password(api_client):
    user = UserFactory(email='reset2@example.com')
    otp_code = request_and_get_otp(api_client, user.email)

    response = api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': otp_code,
        'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
    })

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert check_password(NEW_PASSWORD, user.password)
    assert not check_password(DEFAULT_PASSWORD, user.password)


def test_confirm_old_password_no_longer_works(api_client):
    user = UserFactory(email='reset3@example.com')
    otp_code = request_and_get_otp(api_client, user.email)
    api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': otp_code,
        'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
    })

    login_response = api_client.post(reverse('login'), {
        'email': user.email, 'password': DEFAULT_PASSWORD,
    })
    assert login_response.status_code == status.HTTP_400_BAD_REQUEST


def test_confirm_invalid_otp(api_client):
    user = UserFactory(email='reset4@example.com')
    request_and_get_otp(api_client, user.email)

    response = api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': '000000',
        'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'remaining_attempts' in response.data


def test_confirm_five_wrong_attempts_then_locked(api_client):
    user = UserFactory(email='reset5@example.com')
    request_and_get_otp(api_client, user.email)

    for _ in range(5):
        api_client.post(CONFIRM_URL, {
            'email': user.email, 'otp': '000000',
            'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
        })

    locked = api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': '000000',
        'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
    })
    assert locked.status_code == status.HTTP_400_BAD_REQUEST
    assert 'too many attempts' in str(locked.data).lower()


def test_confirm_expired_otp(api_client):
    user = UserFactory(email='reset6@example.com')
    otp_code = request_and_get_otp(api_client, user.email)
    OTP.objects.filter(user=user).update(expires_at=timezone.now() - timedelta(minutes=1))

    response = api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': otp_code,
        'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'expired' in str(response.data).lower()


def test_confirm_password_mismatch(api_client):
    user = UserFactory(email='reset7@example.com')
    otp_code = request_and_get_otp(api_client, user.email)

    response = api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': otp_code,
        'new_password': NEW_PASSWORD, 'new_password2': 'SomethingElse123!',
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_confirm_otp_cannot_be_reused(api_client):
    user = UserFactory(email='reset8@example.com')
    otp_code = request_and_get_otp(api_client, user.email)
    api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': otp_code,
        'new_password': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
    })

    second_attempt = api_client.post(CONFIRM_URL, {
        'email': user.email, 'otp': otp_code,
        'new_password': 'AnotherPass789!', 'new_password2': 'AnotherPass789!',
    })
    assert second_attempt.status_code == status.HTTP_400_BAD_REQUEST
