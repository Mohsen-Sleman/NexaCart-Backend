import pytest
from django.core import mail
from django.urls import reverse
from rest_framework import status
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

REGISTER_URL = reverse('register')  # adjust the name to match your urls.py if different

VALID_PAYLOAD = {
    'email': 'newuser@example.com',
    'first_name': 'New',
    'last_name': 'User',
    'password': 'StrongPass123!',
    'password2': 'StrongPass123!',
}


def test_register_without_phone_succeeds(api_client):
    """
    phone is optional - this must be a clean 201.
    """
    response = api_client.post(REGISTER_URL, VALID_PAYLOAD)

    assert response.status_code == status.HTTP_201_CREATED
    user = type(UserFactory()).objects.get(email=VALID_PAYLOAD['email'])
    assert user.phone is None
    assert user.is_verified is False


def test_register_with_phone_succeeds(api_client):
    payload = {**VALID_PAYLOAD, 'email': 'withphone@example.com', 'phone': '+963911111111'}
    response = api_client.post(REGISTER_URL, payload)
    assert response.status_code == status.HTTP_201_CREATED


def test_register_sends_otp_email(api_client):
    api_client.post(REGISTER_URL, VALID_PAYLOAD)
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [VALID_PAYLOAD['email']]


def test_register_missing_required_fields(api_client):
    response = api_client.post(REGISTER_URL, {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    for field in ('email', 'first_name', 'last_name', 'password', 'password2'):
        assert field in response.data


def test_register_password_mismatch(api_client):
    payload = {**VALID_PAYLOAD, 'password2': 'Different123!'}
    response = api_client.post(REGISTER_URL, payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_weak_password(api_client):
    payload = {**VALID_PAYLOAD, 'email': 'weak@example.com',
               'password': '12345678', 'password2': '12345678'}
    response = api_client.post(REGISTER_URL, payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'password' in response.data


def test_register_duplicate_email(api_client):
    UserFactory(email=VALID_PAYLOAD['email'])
    response = api_client.post(REGISTER_URL, VALID_PAYLOAD)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in response.data


def test_register_duplicate_phone(api_client):
    UserFactory(phone='+963922222222')
    payload = {**VALID_PAYLOAD, 'email': 'other@example.com', 'phone': '+963922222222'}
    response = api_client.post(REGISTER_URL, payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'phone' in response.data


def test_register_invalid_email_format(api_client):
    payload = {**VALID_PAYLOAD, 'email': 'not-an-email'}
    response = api_client.post(REGISTER_URL, payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
