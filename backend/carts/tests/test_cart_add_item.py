import pytest
from django.urls import reverse
from rest_framework import status
from carts.models import Cart, CartItem
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

ADD_ITEM_URL = reverse('cart-item-create')


def test_add_item_requires_authentication(api_client):
    variant = ProductVariantFactory()
    response = api_client.post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 1})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_add_item_creates_cart_lazily(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory()
    assert Cart.objects.filter(user=user).exists() is False

    auth_client(user).post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 1})

    assert Cart.objects.filter(user=user).exists() is True


def test_add_new_item_success(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory()

    response = auth_client(user).post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 2})

    assert response.status_code == status.HTTP_201_CREATED
    item = CartItem.objects.get(cart__user=user, variant=variant)
    assert item.quantity == 2


def test_add_existing_variant_merges_quantity(auth_client):
    """
    The core agreed behavior for this endpoint: adding the same variant a
    second time ADDS to the existing quantity, it doesn't replace it and
    doesn't create a second row.
    """
    user = UserFactory()
    variant = ProductVariantFactory()
    client = auth_client(user)

    client.post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 2})
    response = client.post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 3})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['quantity'] == 5  # 2 + 3, not 3
    assert CartItem.objects.filter(cart__user=user, variant=variant).count() == 1


def test_add_different_variants_creates_separate_lines(auth_client):
    user = UserFactory()
    client = auth_client(user)
    variant_a = ProductVariantFactory()
    variant_b = ProductVariantFactory()

    client.post(ADD_ITEM_URL, {'variant': variant_a.id, 'quantity': 1})
    client.post(ADD_ITEM_URL, {'variant': variant_b.id, 'quantity': 1})

    assert CartItem.objects.filter(cart__user=user).count() == 2


def test_add_item_quantity_must_be_at_least_one(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory()

    response = auth_client(user).post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 0})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_add_item_rejects_inactive_variant(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory(is_active=False)

    response = auth_client(user).post(ADD_ITEM_URL, {'variant': variant.id, 'quantity': 1})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_add_item_rejects_unknown_variant(auth_client):
    user = UserFactory()
    response = auth_client(user).post(ADD_ITEM_URL, {'variant': 999999, 'quantity': 1})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
