import pytest
from decimal import Decimal
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from orders.models import Order, CouponUsage
from coupons.models import Coupon
from coupons.factories import CouponFactory
from carts.factories import CartItemFactory
from addresses.factories import AddressFactory
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

CHECKOUT_URL = reverse('checkout')


def setup_cart(user, price='100.00', quantity=1):
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(price=price, stock=100)
    CartItemFactory(cart__user=user, variant=variant, quantity=quantity)
    return address


# ------------------------------------------------------------------ success
def test_checkout_with_valid_percentage_coupon(auth_client):
    user = UserFactory()
    address = setup_cart(user, price='100.00')
    coupon = CouponFactory(discount_type=Coupon.TYPE_PERCENTAGE, discount_value=20)

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_201_CREATED
    order = Order.objects.get(user=user)
    assert order.discount_amount == Decimal('20.00')
    assert order.total_amount == order.subtotal + order.shipping_fee - order.discount_amount


def test_checkout_without_coupon_code_still_works(auth_client):
    """coupon_code is optional - omitting the field entirely must not error."""
    user = UserFactory()
    address = setup_cart(user)

    response = auth_client(user).post(CHECKOUT_URL, {'address_id': address.id})

    assert response.status_code == status.HTTP_201_CREATED
    order = Order.objects.get(user=user)
    assert order.discount_amount == Decimal('0.00')


def test_checkout_coupon_creates_usage_record_and_increments_count(auth_client):
    user = UserFactory()
    address = setup_cart(user)
    coupon = CouponFactory(used_count=3)

    auth_client(user).post(CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code})

    order = Order.objects.get(user=user)
    usage = CouponUsage.objects.get(coupon=coupon, user=user)
    assert usage.order == order
    coupon.refresh_from_db()
    assert coupon.used_count == 4  # 3 + 1


def test_checkout_coupon_used_by_a_different_user_is_unaffected(auth_client):
    """SAVE20 being used by user A must never block user B from using it too."""
    coupon = CouponFactory(code='SHARED20')
    other_user = UserFactory()
    CouponUsage.objects.create(
        coupon=coupon, user=other_user,
        order=Order.objects.create(
            user=other_user, subtotal=Decimal('10.00'), shipping_fee=Decimal('5.00'),
            total_amount=Decimal('15.00'), full_name='x', phone='x',
            country='x', city='x', street='x',
        ),
    )

    user = UserFactory()
    address = setup_cart(user)

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_201_CREATED


# --------------------------------------------------------------- rejections
def test_checkout_unknown_coupon_code_rejected(auth_client):
    user = UserFactory()
    address = setup_cart(user)

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': 'DOESNOTEXIST'}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_expired_coupon_rejected(auth_client):
    user = UserFactory()
    address = setup_cart(user)
    coupon = CouponFactory(
        start_date=timezone.now() - timedelta(days=30),
        end_date=timezone.now() - timedelta(days=1),
    )

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_coupon_below_min_order_amount_rejected(auth_client):
    user = UserFactory()
    address = setup_cart(user, price='10.00')  # subtotal = 10
    coupon = CouponFactory(min_order_amount=Decimal('500.00'))

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_coupon_usage_limit_reached_rejected(auth_client):
    user = UserFactory()
    address = setup_cart(user)
    coupon = CouponFactory(usage_limit=5, used_count=5)

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.filter(user=user).exists() is False


def test_checkout_coupon_already_used_by_this_user_rejected(auth_client):
    """The rule this whole CouponUsage table exists for."""
    user = UserFactory()
    coupon = CouponFactory()
    earlier_order = Order.objects.create(
        user=user, status=Order.STATUS_DELIVERED,
        subtotal=Decimal('10.00'), shipping_fee=Decimal('5.00'),
        total_amount=Decimal('15.00'), full_name='x', phone='x',
        country='x', city='x', street='x',
    )
    CouponUsage.objects.create(coupon=coupon, user=user, order=earlier_order)
    address = setup_cart(user)

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'already used' in str(response.data).lower()
    # Only the earlier order exists - no second order got created.
    assert Order.objects.filter(user=user).count() == 1


def test_checkout_rejected_coupon_does_not_touch_stock_or_cart(auth_client):
    """
    Same all-or-nothing principle as the stock check: a coupon rejection
    must roll back cleanly - nothing partially applied.
    """
    user = UserFactory()
    address = setup_cart(user)
    variant = user.cart.items.first().variant
    stock_before = variant.stock
    coupon = CouponFactory(min_order_amount=Decimal('999999.00'))  # guaranteed to fail

    response = auth_client(user).post(
        CHECKOUT_URL, {'address_id': address.id, 'coupon_code': coupon.code}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    variant.refresh_from_db()
    assert variant.stock == stock_before
    assert user.cart.items.exists() is True  # cart was NOT emptied
