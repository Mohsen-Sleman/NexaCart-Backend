import pytest
from django.urls import reverse
from rest_framework import status
from users.factories import UserFactory, DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db

LOGIN_URL = reverse('login')
LOGOUT_URL = reverse('logout')
REFRESH_URL = reverse('token-refresh')


def login(api_client, user):
    """Goes through the real login endpoint to get a genuine access+refresh pair."""
    response = api_client.post(LOGIN_URL, {'email': user.email, 'password': DEFAULT_PASSWORD})
    assert response.status_code == status.HTTP_200_OK
    return response.data['access'], response.data['refresh']


def test_token_refresh_success(api_client):
    user = UserFactory(email='tok1@example.com')
    _access, refresh = login(api_client, user)

    response = api_client.post(REFRESH_URL, {'refresh': refresh})

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data


def test_token_refresh_invalid_token(api_client):
    response = api_client.post(REFRESH_URL, {'refresh': 'not-a-real-token'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_success(api_client):
    user = UserFactory(email='tok2@example.com')
    access, refresh = login(api_client, user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    response = api_client.post(LOGOUT_URL, {'refresh': refresh})

    assert response.status_code == status.HTTP_200_OK


def test_logout_blacklists_refresh_token(api_client):
    """The whole point of logout: the refresh token must stop working afterwards."""
    user = UserFactory(email='tok3@example.com')
    access, refresh = login(api_client, user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    api_client.post(LOGOUT_URL, {'refresh': refresh})

    from rest_framework.test import APIClient
    fresh_client = APIClient()
    response = fresh_client.post(REFRESH_URL, {'refresh': refresh})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_invalid_refresh_token(api_client):
    user = UserFactory(email='tok4@example.com')
    access, _refresh = login(api_client, user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    response = api_client.post(LOGOUT_URL, {'refresh': 'garbage-token'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_logout_requires_authentication(api_client):
    response = api_client.post(LOGOUT_URL, {'refresh': 'anything'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
