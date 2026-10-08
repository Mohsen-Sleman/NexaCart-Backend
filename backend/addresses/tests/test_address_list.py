import pytest
from django.urls import reverse
from rest_framework import status
from addresses.factories import AddressFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

ADDRESS_LIST_URL = reverse('address-list-create')


def test_list_requires_authentication(api_client):
    response = api_client.get(ADDRESS_LIST_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_only_shows_own_addresses(auth_client):
    me = UserFactory()
    someone_else = UserFactory()
    AddressFactory(user=me, city='Mine')
    AddressFactory(user=someone_else, city='NotMine')

    response = auth_client(me).get(ADDRESS_LIST_URL)

    cities = [a['city'] for a in response.data]
    assert cities == ['Mine']


def test_list_empty_for_new_user(auth_client):
    user = UserFactory()
    response = auth_client(user).get(ADDRESS_LIST_URL)
    assert response.data == []


def test_list_includes_phone_and_full_name(auth_client):
    user = UserFactory()
    AddressFactory(user=user, full_name='Jane Doe', phone='+963900000099')

    response = auth_client(user).get(ADDRESS_LIST_URL)

    assert response.data[0]['full_name'] == 'Jane Doe'
    assert response.data[0]['phone'] == '+963900000099'
