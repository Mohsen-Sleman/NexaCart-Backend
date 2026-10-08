import factory
from factory.django import DjangoModelFactory
from datetime import timedelta
from django.utils import timezone
from .models import Coupon


class CouponFactory(DjangoModelFactory):
    class Meta:
        model = Coupon
        django_get_or_create = ('code',)

    code = factory.Sequence(lambda n: f'COUPON{n}')
    discount_type = Coupon.TYPE_FIXED
    discount_value = 10
    max_discount_amount = None
    min_order_amount = 0
    usage_limit = None
    used_count = 0
    start_date = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))
    end_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    is_active = True
