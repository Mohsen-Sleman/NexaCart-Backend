import pytest
from decimal import Decimal
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from coupons.factories import CouponFactory
from coupons.models import Coupon
from carts.factories import CartItemFactory
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

PREVIEW_URL = reverse('coupon-preview')  


def give_user_a_cart(user, price='100.00', quantity=1):
    variant = ProductVariantFactory(price=price)
    CartItemFactory(cart__user=user, variant=variant, quantity=quantity)


def test_preview_requires_authentication(api_client):
    response = api_client.post(PREVIEW_URL, {'code': 'ANY'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_preview_empty_cart_rejected(auth_client):
    user = UserFactory()  # no cart items at all
    coupon = CouponFactory()

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'empty' in str(response.data).lower()

def test_preview_unknown_code(auth_client):
    user = UserFactory()
    give_user_a_cart(user)

    response = auth_client(user).post(PREVIEW_URL, {'code': 'DOESNOTEXIST'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_preview_code_is_case_insensitive(auth_client):
    user = UserFactory()
    give_user_a_cart(user)
    CouponFactory(code='SAVE20')

    response = auth_client(user).post(PREVIEW_URL, {'code': 'save20'})

    assert response.status_code == status.HTTP_200_OK

def test_preview_success_percentage(auth_client):
    user = UserFactory()
    give_user_a_cart(user, price='100.00', quantity=1)
    coupon = CouponFactory(discount_type=Coupon.TYPE_PERCENTAGE, discount_value=20)

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_200_OK
    assert Decimal(response.data['subtotal']) == Decimal('100.00')
    assert Decimal(response.data['discount_amount']) == Decimal('20.00')
    assert Decimal(response.data['total_after_discount']) == Decimal('80.00')


def test_preview_success_fixed(auth_client):
    user = UserFactory()
    give_user_a_cart(user, price='100.00', quantity=2)  # subtotal = 200
    coupon = CouponFactory(discount_type=Coupon.TYPE_FIXED, discount_value=30)

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert Decimal(response.data['subtotal']) == Decimal('200.00')
    assert Decimal(response.data['discount_amount']) == Decimal('30')
    assert Decimal(response.data['total_after_discount']) == Decimal('170.00')


def test_preview_inactive_coupon_rejected(auth_client):
    user = UserFactory()
    give_user_a_cart(user)
    coupon = CouponFactory(is_active=False)

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_preview_expired_coupon_rejected(auth_client):
    user = UserFactory()
    give_user_a_cart(user)
    coupon = CouponFactory(
        start_date=timezone.now() - timedelta(days=30),
        end_date=timezone.now() - timedelta(days=1),
    )

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_preview_usage_limit_reached_rejected(auth_client):
    user = UserFactory()
    give_user_a_cart(user)
    coupon = CouponFactory(usage_limit=5, used_count=5)

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_preview_below_min_order_amount_rejected(auth_client):
    user = UserFactory()
    give_user_a_cart(user, price='10.00')  # subtotal = 10
    coupon = CouponFactory(min_order_amount=Decimal('500.00'))

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_preview_never_mutates_used_count(auth_client):
    """
    The whole point of this endpoint: it's read-only. Calling it
    repeatedly must never increment used_count - that only happens for
    real at actual checkout (tested in the orders suite).
    """
    user = UserFactory()
    give_user_a_cart(user)
    coupon = CouponFactory(used_count=0)

    for _ in range(3):
        auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    coupon.refresh_from_db()
    assert coupon.used_count == 0


def test_preview_does_not_check_per_user_once_rule(auth_client):
    """
    Deliberate scope boundary: this endpoint can't know about
    CouponUsage/Order (the coupons app stays unaware orders exist - see
    the orders app's models.py for why), so it must still say a coupon is
    valid here even if this exact user already redeemed it for a real
    order. The orders app's checkout is what actually enforces the
    per-user-once rule (tested in the orders suite), not this endpoint.
    """
    from orders.models import Order, CouponUsage  # only this test needs it

    user = UserFactory()
    give_user_a_cart(user)
    coupon = CouponFactory()

    dummy_order = Order.objects.create(
        user=user, status=Order.STATUS_DELIVERED,
        subtotal=Decimal('10.00'), shipping_fee=Decimal('5.00'),
        total_amount=Decimal('15.00'),
        full_name='x', phone='x', country='x', city='x', street='x',
    )
    CouponUsage.objects.create(coupon=coupon, user=user, order=dummy_order)

    response = auth_client(user).post(PREVIEW_URL, {'code': coupon.code})

    assert response.status_code == status.HTTP_200_OK  # preview doesn't know/care
