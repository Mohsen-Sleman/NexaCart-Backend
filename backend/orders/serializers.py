from decimal import Decimal
from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from addresses.models import Address
from products.models import ProductVariant
from coupons.models import Coupon
from .models import Order, OrderItem, CouponUsage


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'sku', 'unit_price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    """
    Read-only in every direction - an Order is never edited through the
    client-facing API once created (status changes are a staff/Admin
    action, same reasoning as Product variant edits).
    """
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'payment_method', 'payment_status',
            'subtotal', 'discount_amount', 'shipping_fee', 'total_amount',
            'full_name', 'phone', 'country', 'city', 'street',
            'building', 'apartment', 'postal_code',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    """
    Write-only input for POST /checkout/. Not a ModelSerializer - creating
    an Order here means: locking stock, validating it, validating the
    optional coupon, snapshotting the address, creating OrderItems,
    decrementing stock, recording coupon usage, and emptying the cart -
    all inside one atomic transaction. That's fundamentally a workflow,
    not a single model insert.
    """
    address_id = serializers.IntegerField()
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_address_id(self, value):
        request = self.context['request']
        try:
            self._address = Address.objects.get(pk=value, user=request.user)
        except Address.DoesNotExist:
            raise serializers.ValidationError("Address not found.")
        return value

    def validate_coupon_code(self, value):
        self._coupon = None
        if not value:
            return value
        try:
            self._coupon = Coupon.objects.get(code__iexact=value)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        address = self._address
        coupon = getattr(self, '_coupon', None)

        cart = getattr(user, 'cart', None)
        if not cart or not cart.items.exists():
            raise serializers.ValidationError({"detail": "Your cart is empty."})

        with transaction.atomic():
            cart_items = list(cart.items.select_related('variant', 'variant__product'))
            variant_ids = [ci.variant_id for ci in cart_items]

            locked_variants = {
                v.id: v for v in
                ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
            }

            # All-or-nothing stock check (agreed behavior) - reject the
            # whole order and say exactly which item is the problem.
            for ci in cart_items:
                variant = locked_variants[ci.variant_id]
                if ci.quantity > variant.stock:
                    raise serializers.ValidationError({
                        "detail": f"Not enough stock for {variant.sku}. "
                                f"Available: {variant.stock}, requested: {ci.quantity}."
                    })

            subtotal = sum(
                locked_variants[ci.variant_id].price * ci.quantity for ci in cart_items
            )

            discount_amount = Decimal('0.00')
            if coupon:
                is_valid, reason = coupon.is_valid_for_amount(subtotal)
                if not is_valid:
                    raise serializers.ValidationError({"detail": reason})

                # check if user use this coupon before 
                if CouponUsage.objects.filter(coupon=coupon, user=user).exists():
                    raise serializers.ValidationError(
                        {"detail": "You have already used this coupon."}
                    )
                discount_amount = coupon.calculate_discount(subtotal)

            shipping_fee = Decimal(str(getattr(settings, 'FLAT_SHIPPING_FEE', '5.00')))
            total_amount = subtotal + shipping_fee - discount_amount

            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                discount_amount=discount_amount,
                shipping_fee=shipping_fee,
                total_amount=total_amount,
                full_name=address.full_name,
                phone=address.phone,
                country=address.country,
                city=address.city,
                street=address.street,
                building=address.building,
                apartment=address.apartment,
                postal_code=address.postal_code,
            )

            for ci in cart_items:
                variant = locked_variants[ci.variant_id]
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    product_name=variant.product.name,
                    sku=variant.sku,
                    unit_price=variant.price,
                    quantity=ci.quantity,
                    subtotal=variant.price * ci.quantity,
                )
                variant.stock -= ci.quantity
                variant.save(update_fields=['stock'])

            if coupon:
                CouponUsage.objects.create(coupon=coupon, user=user, order=order)
                coupon.used_count += 1
                coupon.save(update_fields=['used_count'])

            cart.items.all().delete()  # cart empties fully on success

        return order
