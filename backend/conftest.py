import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Plain, unauthenticated DRF test client - the default for every test."""
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    """
    A client factory: auth_client(user) returns an APIClient already
    carrying that user's JWT access token. A fixture returning a function
    (not a fixed client) because different tests need to authenticate as
    different users.
    """
    def _as(user):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return api_client
    return _as
