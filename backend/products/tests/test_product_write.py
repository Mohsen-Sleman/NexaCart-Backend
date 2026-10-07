import pytest
from django.urls import reverse
from rest_framework import status
from products.factories import CategoryFactory, ProductFactory, ProductVariantFactory
from products.models import Product, ProductVariant
from users.factories import StaffUserFactory, UserFactory

pytestmark = pytest.mark.django_db

PRODUCT_LIST_URL = reverse('product-list-create')


def detail_url(slug):
    return reverse('product-detail', kwargs={'slug': slug})


def valid_payload(category):
    return {
        'category': category.id,
        'name': 'New Gadget',
        'description': 'A gadget.',
        'brand': 'TestBrand',
        'variants': [{'sku': 'GADGET-1', 'price': '49.99', 'stock': 5}],
    }


# ------------------------------------------------------------------ create
def test_create_requires_authentication(api_client):
    category = CategoryFactory()
    response = api_client.post(PRODUCT_LIST_URL, valid_payload(category), format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_requires_staff_not_just_login(auth_client):
    category = CategoryFactory()
    regular_user = UserFactory()

    response = auth_client(regular_user).post(PRODUCT_LIST_URL, valid_payload(category), format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_success_as_staff(auth_client):
    staff = StaffUserFactory()
    category = CategoryFactory()

    response = auth_client(staff).post(PRODUCT_LIST_URL, valid_payload(category), format='json')

    assert response.status_code == status.HTTP_201_CREATED
    product = Product.objects.get(name='New Gadget')
    assert product.variants.count() == 1
    assert product.variants.first().sku == 'GADGET-1'


def test_create_without_variants_fails(auth_client):
    staff = StaffUserFactory()
    category = CategoryFactory()
    payload = valid_payload(category)
    payload['variants'] = []

    response = auth_client(staff).post(PRODUCT_LIST_URL, payload, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'variants' in response.data
    assert Product.objects.filter(name='New Gadget').exists() is False


def test_create_response_excludes_slug_and_images(auth_client):
    """
    Documents a deliberate design choice: ProductWriteSerializer's fields
    don't include slug/images - the create response is intentionally
    narrower than the detail view's. If this ever changes on purpose,
    update this test, don't just let it fail silently.
    """
    staff = StaffUserFactory()
    category = CategoryFactory()

    response = auth_client(staff).post(PRODUCT_LIST_URL, valid_payload(category), format='json')

    assert 'slug' not in response.data
    assert 'images' not in response.data


# ------------------------------------------------------------------ update
def test_update_requires_authentication(api_client):
    product = ProductFactory()
    response = api_client.patch(detail_url(product.slug), {'description': 'x'}, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_requires_staff(auth_client):
    product = ProductFactory()
    regular_user = UserFactory()

    response = auth_client(regular_user).patch(
        detail_url(product.slug), {'description': 'new desc'}, format='json'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_basic_fields_success(auth_client):
    staff = StaffUserFactory()
    product = ProductFactory(description='old')

    response = auth_client(staff).patch(
        detail_url(product.slug), {'description': 'new desc'}, format='json'
    )

    assert response.status_code == status.HTTP_200_OK
    product.refresh_from_db()
    assert product.description == 'new desc'


def test_update_ignores_variants_in_payload(auth_client):
    """
    Agreed design: PATCH edits product-level fields only. Sending variants
    here must not create/modify any - that's done through the Admin.
    """
    staff = StaffUserFactory()
    product = ProductFactory()
    ProductVariantFactory(product=product)  # exactly one existing variant

    response = auth_client(staff).patch(
        detail_url(product.slug),
        {'description': 'updated', 'variants': [{'sku': 'SHOULD-NOT-EXIST', 'price': '1.00', 'stock': 1}]},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert product.variants.count() == 1
    assert not ProductVariant.objects.filter(sku='SHOULD-NOT-EXIST').exists()


# ------------------------------------------------------------------ delete
def test_delete_requires_authentication(api_client):
    product = ProductFactory()
    response = api_client.delete(detail_url(product.slug))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_requires_staff(auth_client):
    product = ProductFactory()
    regular_user = UserFactory()

    response = auth_client(regular_user).delete(detail_url(product.slug))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_success_cascades_variants(auth_client):
    staff = StaffUserFactory()
    product = ProductFactory()
    variant = ProductVariantFactory(product=product)

    response = auth_client(staff).delete(detail_url(product.slug))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Product.objects.filter(pk=product.pk).exists() is False
    assert ProductVariant.objects.filter(pk=variant.pk).exists() is False
