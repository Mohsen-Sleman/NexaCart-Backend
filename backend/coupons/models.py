from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class Coupon(models.Model):
    TYPE_PERCENTAGE = 'percentage'
    TYPE_FIXED = 'fixed'
    DISCOUNT_TYPE_CHOICES = [
        (TYPE_PERCENTAGE, 'Percentage'),
        (TYPE_FIXED, 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.discount_type == self.TYPE_PERCENTAGE and self.discount_value > 100:
            raise ValidationError({"discount_value": "Percentage discount cannot exceed 100."})
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError({"end_date": "End date must be after start date."})

    def is_valid_for_amount(self, order_subtotal):
        now = timezone.now()
        if not self.is_active:
            return False, "This coupon is not active."
        if now < self.start_date or now > self.end_date:
            return False, "This coupon is not currently valid."
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, "This coupon has reached its usage limit."
        if order_subtotal < self.min_order_amount:
            return False, f"Order must be at least {self.min_order_amount} to use this coupon."
        return True, None

    def calculate_discount(self, order_subtotal):
        if self.discount_type == self.TYPE_PERCENTAGE:
            discount = order_subtotal * (self.discount_value / Decimal('100'))
        else:
            discount = self.discount_value

        if self.max_discount_amount is not None:
            discount = min(discount, self.max_discount_amount)

        # Never discount more than the order is actually worth.
        return min(discount, order_subtotal)

    def __str__(self):
        return self.code
