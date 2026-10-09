import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from orders.models import Order, OrderItem
from carts.models import CartItem
from carts.factories import CartItemFactory
from addresses.factories import AddressFactory
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

CHECKOUT_URL = reverse('checkout')


def test_checkout_requires_authentication(api_client):
    response = api_client.post(CHECKOUT_URL, {'address_id': 1})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_checkout_success_creates_order(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user, full_name='Jane Doe', phone='+963911111111')
    variant = ProductVariantFactory(price='50.00', stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=2)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    assert response.status_code == status.HTTP_201_CREATED
    order = Order.objects.get(user=user)
    assert order.status == Order.STATUS_PENDING
    assert order.payment_status == Order.PAYMENT_UNPAID
    assert order.subtotal == Decimal('100.00')  # 50 * 2
    assert order.discount_amount == Decimal('0.00')
    assert order.total_amount == order.subtotal + order.shipping_fee
    # shipping snapshot copied from the Address, not the User
    assert order.full_name == 'Jane Doe'
    assert order.phone == '+963911111111'
    assert order.city == address.city


def test_checkout_creates_matching_order_items(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(sku='SKU-X', price='30.00', stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=3)

    auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    order = Order.objects.get(user=user)
    item = OrderItem.objects.get(order=order)
    assert item.sku == 'SKU-X'
    assert item.quantity == 3
    assert item.unit_price == Decimal('30.00')
    assert item.subtotal == Decimal('90.00')


def test_checkout_empties_the_cart(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=1)

    auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    assert CartItem.objects.filter(cart__user=user).exists() is False


def test_checkout_decrements_stock(auth_client):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=4)

    auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    variant.refresh_from_db()
    assert variant.stock == 6  # 10 - 4


def test_checkout_uses_the_address_specified_not_the_default(auth_client):
    """
    Agreed rule: the client must pass address_id explicitly - there's no
    silent fallback to whichever address happens to be is_default=True.
    """
    user = UserFactory()
    default_address = AddressFactory(user=user, city='DefaultCity')  # auto-default
    other_address = AddressFactory(user=user, city='OtherCity')
    assert default_address.is_default is True
    assert other_address.is_default is False
    variant = ProductVariantFactory(stock=10)
    CartItemFactory(cart__user=user, variant=variant, quantity=1)

    auth_client(user).post(CHECKOUT_URL, {'address_id': other_address.id})

    order = Order.objects.get(user=user)
    assert order.city == 'OtherCity'  # the one explicitly passed, not the default
