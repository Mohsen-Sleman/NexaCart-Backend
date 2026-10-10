import pytest
from django.urls import reverse
from rest_framework import status
from products.factories import ProductFactory
from reviews.factories import ReviewFactory

pytestmark = pytest.mark.django_db


def list_url(slug):
    return reverse('product-review-list', kwargs={'slug': slug})


def test_list_is_public(api_client):
    product = ProductFactory()
    response = api_client.get(list_url(product.slug))
    assert response.status_code == status.HTTP_200_OK


def test_list_only_shows_reviews_for_that_product(api_client):
    product_a = ProductFactory(name='A')
    product_b = ProductFactory(name='B')
    ReviewFactory(product=product_a, comment='About A')
    ReviewFactory(product=product_b, comment='About B')

    response = api_client.get(list_url(product_a.slug))

    comments = [r['comment'] for r in response.data]
    assert comments == ['About A']


def test_list_unknown_product_404(api_client):
    response = api_client.get(list_url('does-not-exist'))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_inactive_product_404(api_client):
    product = ProductFactory(is_active=False)
    response = api_client.get(list_url(product.slug))
    assert response.status_code == status.HTTP_404_NOT_FOUND
