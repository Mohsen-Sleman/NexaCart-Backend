import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from carts.models import Cart
from carts.factories import CartItemFactory
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

CART_URL = reverse('cart-detail')


def test_get_cart_requires_authentication(api_client):
    response = api_client.get(CART_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_cart_creates_it_lazily(auth_client):
    user = UserFactory()
    assert Cart.objects.filter(user=user).exists() is False

    response = auth_client(user).get(CART_URL)

    assert response.status_code == status.HTTP_200_OK
    assert Cart.objects.filter(user=user).exists() is True


def test_get_cart_second_call_does_not_create_duplicate(auth_client):
    user = UserFactory()
    client = auth_client(user)
    client.get(CART_URL)
    client.get(CART_URL)

    assert Cart.objects.filter(user=user).count() == 1


def test_get_cart_is_empty_by_default(auth_client):
    user = UserFactory()
    response = auth_client(user).get(CART_URL)
    assert response.data['items'] == []
    assert response.data['total'] == 0


def test_get_cart_shows_items_with_subtotal(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory(price='50.00')
    item = CartItemFactory(cart__user=user, variant=variant, quantity=3)

    response = auth_client(user).get(CART_URL)

    line = response.data['items'][0]
    assert line['quantity'] == 3
    assert Decimal(line['subtotal']) == Decimal('150.00')


def test_get_cart_total_sums_all_lines(auth_client):
    user = UserFactory()
    cart = CartItemFactory(cart__user=user, variant=ProductVariantFactory(price='10.00'), quantity=2).cart
    CartItemFactory(cart=cart, variant=ProductVariantFactory(price='20.00'), quantity=1)

    response = auth_client(user).get(CART_URL)

    assert Decimal(response.data['total']) == Decimal('40.00')  # (10*2) + (20*1)


def test_cart_only_shows_own_items(auth_client):
    me = UserFactory()
    someone_else = UserFactory()
    CartItemFactory(cart__user=someone_else)

    response = auth_client(me).get(CART_URL)

    assert response.data['items'] == []
