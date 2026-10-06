import pytest
from django.urls import reverse
from rest_framework import status
from users.factories import UserFactory, UnverifiedUserFactory, DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db

LOGIN_URL = reverse('login')



def test_login_success(api_client):
    user = UserFactory(email='login1@example.com')

    response = api_client.post(LOGIN_URL, {
        'email': user.email, 'password': DEFAULT_PASSWORD,
    })

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data



def test_login_unverified_user_rejected(api_client):
    user = UnverifiedUserFactory(email='login2@example.com')

    response = api_client.post(LOGIN_URL, {
        'email': user.email, 'password': DEFAULT_PASSWORD,
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'access' not in response.data


def test_login_wrong_password(api_client):
    user = UserFactory(email='login3@example.com')

    response = api_client.post(LOGIN_URL, {
        'email': user.email, 'password': 'WrongPassword!',
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_nonexistent_email(api_client):
    response = api_client.post(LOGIN_URL, {
        'email': 'nobody@example.com', 'password': 'Whatever123!',
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_missing_fields(api_client):
    response = api_client.post(LOGIN_URL, {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_does_not_leak_whether_email_exists(api_client):
    """
    Both 'wrong password' and 'unknown email' should read the same to the
    client - a different message for each lets an attacker enumerate which
    emails are registered.
    """
    UserFactory(email='login4@example.com')

    wrong_password = api_client.post(LOGIN_URL, {
        'email': 'login4@example.com', 'password': 'WrongPassword!',
    })
    unknown_email = api_client.post(LOGIN_URL, {
        'email': 'nobody-at-all@example.com', 'password': 'WrongPassword!',
    })

    assert wrong_password.data == unknown_email.data
