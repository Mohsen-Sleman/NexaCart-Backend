import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from users.factories import UserFactory,UnverifiedUserFactory

pytestmark = pytest.mark.django_db

GOOGLE_LOGIN_URL = reverse('google-login')
User = get_user_model()

GOOGLE_PAYLOAD = {
    'email': 'googleuser@example.com',
    'given_name': 'Google',
    'family_name': 'User',
}

PATCH_TARGET = 'users.views.verify_google_token'


def test_google_login_new_user_creates_account(api_client):
    with patch(PATCH_TARGET, return_value=GOOGLE_PAYLOAD):
        response = api_client.post(GOOGLE_LOGIN_URL, {'access_token': 'fake-valid-token'})

    assert response.status_code == status.HTTP_200_OK
    assert response.data['is_new_user'] is True
    assert 'access' in response.data
    assert 'refresh' in response.data

    user = User.objects.get(email=GOOGLE_PAYLOAD['email'])
    assert user.first_name == 'Google'
    assert user.has_usable_password() is False


def test_google_login_new_user_is_verified_automatically(api_client):
    """Google already confirmed this email belongs to them - no separate OTP step needed."""
    with patch(PATCH_TARGET, return_value=GOOGLE_PAYLOAD):
        api_client.post(GOOGLE_LOGIN_URL, {'access_token': 'fake-valid-token'})

    user = User.objects.get(email=GOOGLE_PAYLOAD['email'])
    assert user.is_verified is True


def test_google_login_existing_unverified_user_becomes_verified(api_client):
    unverified = UnverifiedUserFactory(email=GOOGLE_PAYLOAD['email'])

    with patch(PATCH_TARGET, return_value=GOOGLE_PAYLOAD):
        api_client.post(GOOGLE_LOGIN_URL, {'access_token': 'fake-valid-token'})

    unverified.refresh_from_db()
    assert unverified.is_verified is True


def test_google_login_existing_user_signs_in_without_duplicating(api_client):
    existing = UserFactory(email=GOOGLE_PAYLOAD['email'])

    with patch(PATCH_TARGET, return_value=GOOGLE_PAYLOAD):
        response = api_client.post(GOOGLE_LOGIN_URL, {'access_token': 'fake-valid-token'})

    assert response.status_code == status.HTTP_200_OK
    assert response.data['is_new_user'] is False
    assert response.data['user']['email'] == existing.email
    assert User.objects.filter(email=GOOGLE_PAYLOAD['email']).count() == 1


def test_google_login_invalid_token_rejected(api_client):
    with patch(PATCH_TARGET, return_value=None):
        response = api_client.post(GOOGLE_LOGIN_URL, {'access_token': 'garbage'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.count() == 0


def test_google_login_missing_access_token(api_client):
    response = api_client.post(GOOGLE_LOGIN_URL, {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
