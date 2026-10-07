import pytest
from django.urls import reverse
from rest_framework import status
from products.factories import CategoryFactory

pytestmark = pytest.mark.django_db

CATEGORY_LIST_URL = reverse('category-list')


def test_category_list_is_public(api_client):
    response = api_client.get(CATEGORY_LIST_URL)
    assert response.status_code == status.HTTP_200_OK


def test_category_list_only_shows_active(api_client):
    CategoryFactory(name='Active One', is_active=True)
    CategoryFactory(name='Hidden One', is_active=False)

    response = api_client.get(CATEGORY_LIST_URL)

    names = [c['name'] for c in response.data]
    assert 'Active One' in names
    assert 'Hidden One' not in names
