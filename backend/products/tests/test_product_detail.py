import pytest
from django.urls import reverse
from rest_framework import status
from products.factories import (
    ProductFactory, ProductVariantFactory, ProductImageFactory,
    ProductAttributeFactory, VariantAttributeFactory,
)
from users.factories import StaffUserFactory

pytestmark = pytest.mark.django_db


def detail_url(slug):
    return reverse('product-detail', kwargs={'slug': slug})


def test_detail_success(api_client):
    product = ProductFactory(name='iPhone 15')

    response = api_client.get(detail_url(product.slug))

    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'iPhone 15'


def test_detail_includes_nested_variants_attributes_images(api_client):
    product = ProductFactory()
    variant = ProductVariantFactory(product=product, sku='SKU-1')
    VariantAttributeFactory(variant=variant, key='Color', value='Black')
    ProductAttributeFactory(product=product, key='Warranty', value='1 Year')
    ProductImageFactory(product=product, is_primary=True)

    response = api_client.get(detail_url(product.slug))

    assert len(response.data['variants']) == 1
    assert response.data['variants'][0]['sku'] == 'SKU-1'
    assert response.data['variants'][0]['attributes'][0]['value'] == 'Black'
    assert response.data['attributes'][0]['key'] == 'Warranty'
    assert len(response.data['images']) == 1


def test_detail_unknown_slug_404(api_client):
    response = api_client.get(detail_url('does-not-exist'))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_inactive_product_404_for_guest(api_client):
    product = ProductFactory(is_active=False)
    response = api_client.get(detail_url(product.slug))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_inactive_product_visible_to_staff(auth_client):
    staff = StaffUserFactory()
    product = ProductFactory(is_active=False)

    response = auth_client(staff).get(detail_url(product.slug))

    assert response.status_code == status.HTTP_200_OK
