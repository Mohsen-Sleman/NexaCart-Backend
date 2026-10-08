import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from coupons.factories import CouponFactory
from coupons.models import Coupon

pytestmark = pytest.mark.django_db


# --------------------------------------------------------- is_valid_for_amount
def test_valid_coupon_passes():
    coupon = CouponFactory()
    is_valid, reason = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is True
    assert reason is None


def test_inactive_coupon_rejected():
    coupon = CouponFactory(is_active=False)
    is_valid, reason = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is False
    assert 'not active' in reason.lower()


def test_not_started_yet_rejected():
    coupon = CouponFactory(start_date=timezone.now() + timedelta(days=5))
    is_valid, _ = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is False


def test_expired_rejected():
    coupon = CouponFactory(
        start_date=timezone.now() - timedelta(days=30),
        end_date=timezone.now() - timedelta(days=1),
    )
    is_valid, _ = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is False


def test_usage_limit_reached_rejected():
    coupon = CouponFactory(usage_limit=5, used_count=5)
    is_valid, reason = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is False
    assert 'usage limit' in reason.lower()


def test_usage_limit_not_yet_reached_passes():
    coupon = CouponFactory(usage_limit=5, used_count=4)
    is_valid, _ = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is True


def test_unlimited_usage_when_limit_is_none():
    coupon = CouponFactory(usage_limit=None, used_count=99999)
    is_valid, _ = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is True


def test_below_min_order_amount_rejected():
    coupon = CouponFactory(min_order_amount=Decimal('500.00'))
    is_valid, reason = coupon.is_valid_for_amount(Decimal('100.00'))
    assert is_valid is False
    assert '500' in reason


def test_exactly_at_min_order_amount_passes():
    coupon = CouponFactory(min_order_amount=Decimal('500.00'))
    is_valid, _ = coupon.is_valid_for_amount(Decimal('500.00'))
    assert is_valid is True  # boundary: >= not >


# ------------------------------------------------------------ calculate_discount
def test_percentage_discount():
    coupon = CouponFactory(discount_type=Coupon.TYPE_PERCENTAGE, discount_value=20)
    discount = coupon.calculate_discount(Decimal('100.00'))
    assert discount == Decimal('20.00')


def test_fixed_discount():
    coupon = CouponFactory(discount_type=Coupon.TYPE_FIXED, discount_value=15)
    discount = coupon.calculate_discount(Decimal('100.00'))
    assert discount == Decimal('15')


def test_percentage_discount_capped_by_max_discount_amount():
    coupon = CouponFactory(
        discount_type=Coupon.TYPE_PERCENTAGE, discount_value=50,
        max_discount_amount=Decimal('30.00'),
    )
    discount = coupon.calculate_discount(Decimal('200.00'))  # 50% would be 100
    assert discount == Decimal('30.00')  # capped


def test_percentage_discount_under_cap_is_unaffected():
    coupon = CouponFactory(
        discount_type=Coupon.TYPE_PERCENTAGE, discount_value=10,
        max_discount_amount=Decimal('100.00'),
    )
    discount = coupon.calculate_discount(Decimal('200.00'))  # 10% = 20, well under cap
    assert discount == Decimal('20.00')


def test_discount_never_exceeds_order_subtotal():
    """A $1000 fixed coupon against a $50 order can only discount $50, not $1000."""
    coupon = CouponFactory(discount_type=Coupon.TYPE_FIXED, discount_value=1000)
    discount = coupon.calculate_discount(Decimal('50.00'))
    assert discount == Decimal('50.00')
