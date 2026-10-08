import pytest
from django.urls import reverse
from rest_framework import status
from addresses.models import Address
from addresses.factories import AddressFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


def address_url(address_id):
    return reverse('address-detail', kwargs={'pk': address_id}) 


# ------------------------------------------------------------------ update
def test_update_requires_authentication(api_client):
    address = AddressFactory()
    response = api_client.patch(address_url(address.id), {'city': 'Homs'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_basic_fields_success(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user, city='Damascus')

    response = auth_client(user).patch(address_url(address.id), {'city': 'Homs'})

    assert response.status_code == status.HTTP_200_OK
    address.refresh_from_db()
    assert address.city == 'Homs'


def test_setting_is_default_via_patch_switches_previous(auth_client):
    user = UserFactory()
    first = AddressFactory(user=user)  # auto-default
    second = AddressFactory(user=user)
    assert second.is_default is False

    response = auth_client(user).patch(address_url(second.id), {'is_default': True})

    assert response.status_code == status.HTTP_200_OK
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_default is False
    assert second.is_default is True


def test_update_someone_elses_address_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    address = AddressFactory(user=owner, city='Original')

    response = auth_client(attacker).patch(address_url(address.id), {'city': 'Hacked'})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    address.refresh_from_db()
    assert address.city == 'Original'


# ------------------------------------------------------------------ delete
def test_delete_requires_authentication(api_client):
    address = AddressFactory()
    response = api_client.delete(address_url(address.id))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_non_default_address_success(auth_client):
    user = UserFactory()
    AddressFactory(user=user)  # default, kept
    second = AddressFactory(user=user)  # not default - deletable
    assert second.is_default is False

    response = auth_client(user).delete(address_url(second.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Address.objects.filter(pk=second.pk).exists() is False


def test_delete_default_address_is_blocked(auth_client):
    user = UserFactory()
    default_address = AddressFactory(user=user)
    AddressFactory(user=user)  

    response = auth_client(user).delete(address_url(default_address.id))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Address.objects.filter(pk=default_address.pk).exists() is True


def test_delete_only_address_is_blocked_even_with_no_alternative(auth_client):
    """
    The stricter, agreed rule: blocked whether or not another address
    exists to fall back to - not just 'blocked if it's literally the only one'.
    """
    user = UserFactory()
    only_address = AddressFactory(user=user)  # auto-default, and the only one

    response = auth_client(user).delete(address_url(only_address.id))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Address.objects.filter(pk=only_address.pk).exists() is True


def test_delete_someone_elses_address_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    AddressFactory(user=owner)  # owner's default
    non_default = AddressFactory(user=owner)

    response = auth_client(attacker).delete(address_url(non_default.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Address.objects.filter(pk=non_default.pk).exists() is True
