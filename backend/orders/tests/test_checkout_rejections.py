import pytest
from django.urls import reverse
from rest_framework import status
from orders.models import Order
from carts.factories import CartItemFactory
from addresses.factories import AddressFactory
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

CHECKOUT_URL = reverse('checkout')


def test_checkout_empty_cart_rejected(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'empty' in str(response.data).lower()
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_unknown_address_rejected(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory(stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=1)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': 999999})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_rejects_another_users_address(auth_client):
    """Same ownership-scoping principle as everywhere else - you can't
    checkout to an address id that exists but isn't yours."""
    user = UserFactory()
    someone_else_address = AddressFactory(user=UserFactory())
    variant = ProductVariantFactory(stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=1)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': someone_else_address.id})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_insufficient_stock_rejected(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(sku='LOW-STOCK', stock=2)
    CartItemFactory(cart__user=user, variant=variant, quantity=5)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'LOW-STOCK' in str(response.data)
    # Nothing committed: no order, and the stock itself is untouched.
    assert Order.objects.filter(user=user).exists() is False
    variant.refresh_from_db()
    assert variant.stock == 2


def test_checkout_insufficient_stock_is_all_or_nothing(auth_client):
    """
    Two items in the cart: one has enough stock, the other doesn't. The
    agreed behavior is the WHOLE order is rejected - the item that was
    fine must not get partially checked out or have its stock touched.
    """
    user = UserFactory()
    address = AddressFactory(user=user)
    plenty = ProductVariantFactory(sku='PLENTY', stock=100)
    scarce = ProductVariantFactory(sku='SCARCE', stock=1)
    CartItemFactory(cart__user=user, variant=plenty, quantity=5)
    CartItemFactory(cart__user=user, variant=scarce, quantity=5)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False
    plenty.refresh_from_db()
    scarce.refresh_from_db()
    assert plenty.stock == 100  # untouched, even though it "would have" worked
    assert scarce.stock == 1
