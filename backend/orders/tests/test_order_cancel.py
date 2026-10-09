import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from orders.models import Order, CouponUsage
from orders.factories import OrderFactory, OrderItemFactory
from coupons.factories import CouponFactory
from products.factories import ProductVariantFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


def cancel_url(order_id):
    return reverse('order-cancel', kwargs={'pk': order_id})


def test_cancel_requires_authentication(api_client):
    order = OrderFactory()
    response = api_client.post(cancel_url(order.id))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize('cancellable_status', [Order.STATUS_PENDING, Order.STATUS_PROCESSING])
def test_cancel_succeeds_for_pending_or_processing(auth_client, cancellable_status):
    user = UserFactory()
    order = OrderFactory(user=user, status=cancellable_status)

    response = auth_client(user).post(cancel_url(order.id))

    assert response.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == Order.STATUS_CANCELLED


@pytest.mark.parametrize('blocked_status', [Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
def test_cancel_blocked_once_shipped_or_delivered(auth_client, blocked_status):
    user = UserFactory()
    order = OrderFactory(user=user, status=blocked_status)

    response = auth_client(user).post(cancel_url(order.id))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    order.refresh_from_db()
    assert order.status == blocked_status  # unchanged


def test_cancel_already_cancelled_gives_specific_message(auth_client):
    user = UserFactory()
    order = OrderFactory(user=user, status=Order.STATUS_CANCELLED)

    response = auth_client(user).post(cancel_url(order.id))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'already cancelled' in str(response.data).lower()


def test_cancel_someone_elses_order_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    order = OrderFactory(user=owner, status=Order.STATUS_PENDING)

    response = auth_client(attacker).post(cancel_url(order.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    order.refresh_from_db()
    assert order.status == Order.STATUS_PENDING  # untouched


# -------------------------------------------------------------- side effects
def test_cancel_restores_stock(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory(stock=5)
    order = OrderFactory(user=user, status=Order.STATUS_PENDING)
    OrderItemFactory(order=order, variant=variant, quantity=3)

    auth_client(user).post(cancel_url(order.id))

    variant.refresh_from_db()
    assert variant.stock == 8  # 5 + 3


def test_cancel_handles_a_since_deleted_variant_gracefully(auth_client):
    """
    OrderItem.variant is SET_NULL - if the variant was deleted after the
    order was placed, cancel must still work (just nothing left to
    restore stock to), not crash.
    """
    user = UserFactory()
    order = OrderFactory(user=user, status=Order.STATUS_PENDING)
    item = OrderItemFactory(order=order)
    item.variant = None  # simulate the variant having been deleted since
    item.save(update_fields=['variant'])

    response = auth_client(user).post(cancel_url(order.id))

    assert response.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == Order.STATUS_CANCELLED


def test_cancel_reverses_coupon_usage(auth_client):
    user = UserFactory()
    coupon = CouponFactory(used_count=1)
    order = OrderFactory(user=user, status=Order.STATUS_PENDING, discount_amount=Decimal('10.00'))
    CouponUsage.objects.create(coupon=coupon, user=user, order=order)

    auth_client(user).post(cancel_url(order.id))

    assert CouponUsage.objects.filter(coupon=coupon, user=user).exists() is False
    coupon.refresh_from_db()
    assert coupon.used_count == 0  # 1 - 1


def test_cancel_lets_user_reuse_the_coupon_afterwards(auth_client):
    """The actual point of reversing CouponUsage: it's genuinely usable again."""
    from coupons.models import Coupon as CouponModel

    user = UserFactory()
    coupon = CouponFactory(usage_limit=1,used_count=1)
    order = OrderFactory(user=user, status=Order.STATUS_PENDING)
    CouponUsage.objects.create(coupon=coupon, user=user, order=order)

    auth_client(user).post(cancel_url(order.id))

    is_valid, _reason = CouponModel.objects.get(pk=coupon.pk).is_valid_for_amount(Decimal('100.00'))
    assert is_valid is True
    assert CouponUsage.objects.filter(coupon=coupon, user=user).exists() is False


def test_cancel_order_without_any_coupon_works_fine(auth_client):
    """Most orders have no coupon at all - cancel must not assume one exists."""
    user = UserFactory()
    order = OrderFactory(user=user, status=Order.STATUS_PENDING)

    response = auth_client(user).post(cancel_url(order.id))

    assert response.status_code == status.HTTP_200_OK


def test_cancel_used_count_never_goes_negative(auth_client):
    """Defensive: even if used_count was somehow already 0, cancelling must not make it -1."""
    user = UserFactory()
    coupon = CouponFactory(used_count=0)
    order = OrderFactory(user=user, status=Order.STATUS_PENDING)
    CouponUsage.objects.create(coupon=coupon, user=user, order=order)

    auth_client(user).post(cancel_url(order.id))

    coupon.refresh_from_db()
    assert coupon.used_count == 0  # not -1
