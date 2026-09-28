from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from products.models import ProductVariant
from coupons.models import Coupon


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAYMENT_UNPAID = 'unpaid'
    PAYMENT_PAID = 'paid'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_UNPAID, 'Unpaid'),
        (PAYMENT_PAID, 'Paid'),
    ]

    # PROTECT: an order is a financial/legal record - a user account must
    # never be hard-deleted while orders reference it (same reasoning as
    # Product -> Category).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=20, default='cod')
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_UNPAID
    )

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Shipping snapshot - copied from the chosen Address at checkout time.
    # Deliberately NOT a FK to Address:
    # order must keep showing what was true when it shipped, even if the
    # address is edited or deleted afterwards.
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    building = models.CharField(max_length=100, blank=True, null=True)
    apartment = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # SET_NULL, not CASCADE/PROTECT: if a variant is later deleted, this
    # historical line item must survive (it already has its own snapshot
    # of name/sku/price below) - only the live link becomes null.
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, related_name='order_items'
    )
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.sku} (order #{self.order_id})"


class CouponUsage(models.Model):
    # PROTECT: never let a coupon be deleted once it's actually been
    # redeemed by someone - that would corrupt this historical record.
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name='usages')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupon_usages'
    )
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='coupon_usage')
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['coupon', 'user'], name='unique_coupon_per_user')
        ]

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code} on order #{self.order_id}"
