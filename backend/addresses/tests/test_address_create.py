import pytest
from django.urls import reverse
from rest_framework import status
from addresses.models import Address
from addresses.factories import AddressFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

ADDRESS_LIST_URL = reverse('address-list-create')


def valid_payload(**overrides):
    payload = {
        'country': 'Syria', 'city': 'Aleppo', 'street': 'Al Furqan St',
        'full_name': 'New Recipient', 'phone': '+963911111111',
    }
    payload.update(overrides)
    return payload


def test_create_requires_authentication(api_client):
    response = api_client.post(ADDRESS_LIST_URL, valid_payload())
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_success(auth_client):
    user = UserFactory()
    response = auth_client(user).post(ADDRESS_LIST_URL, valid_payload())

    assert response.status_code == status.HTTP_201_CREATED
    assert Address.objects.filter(user=user, city='Aleppo').exists()


def test_create_missing_required_fields(auth_client):
    user = UserFactory()
    response = auth_client(user).post(ADDRESS_LIST_URL, {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    for field in ('country', 'city', 'street', 'full_name', 'phone'):
        assert field in response.data


def test_cannot_create_address_for_another_user(auth_client):
    """'user' isn't even a field the client can send - it always comes
    from request.user. Sending it should simply be ignored, not error."""
    me = UserFactory()
    other = UserFactory()

    response = auth_client(me).post(ADDRESS_LIST_URL, valid_payload(user=other.id))

    assert response.status_code == status.HTTP_201_CREATED
    created = Address.objects.get(street='Al Furqan St')
    assert created.user == me  # not `other`, regardless of what was sent


# ------------------------------------------------------- auto-default rule
def test_first_address_becomes_default_automatically(auth_client):
    user = UserFactory()
    response = auth_client(user).post(ADDRESS_LIST_URL, valid_payload())

    assert response.data['is_default'] is True


def test_first_address_becomes_default_even_if_explicitly_false(auth_client):
    """
    The rule is absolute: a user's first address is always the default,
    no matter what the client sent - there must never be a user with
    addresses but zero defaults.
    """
    user = UserFactory()
    response = auth_client(user).post(ADDRESS_LIST_URL, valid_payload(is_default=False))

    assert response.data['is_default'] is True


def test_second_address_is_not_default_by_default(auth_client):
    user = UserFactory()
    AddressFactory(user=user)  # first one, auto-default

    response = auth_client(user).post(ADDRESS_LIST_URL, valid_payload())

    assert response.data['is_default'] is False


def test_creating_address_as_default_switches_the_previous_one(auth_client):
    user = UserFactory()
    first = AddressFactory(user=user)  # auto-default
    assert first.is_default is True

    auth_client(user).post(ADDRESS_LIST_URL, valid_payload(is_default=True))

    first.refresh_from_db()
    assert first.is_default is False
    assert Address.objects.filter(user=user, is_default=True).count() == 1


def test_default_switch_is_scoped_per_user(auth_client):
    """Setting MY new address as default must never touch someone else's default."""
    me = UserFactory()
    other = UserFactory()
    other_default = AddressFactory(user=other)  # other's auto-default
    AddressFactory(user=me)  # my own auto-default, not involved here

    auth_client(me).post(ADDRESS_LIST_URL, valid_payload(is_default=True))

    other_default.refresh_from_db()
    assert other_default.is_default is True  # untouched
