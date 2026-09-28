from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from products.models import ProductVariant
from .models import Order
from .serializers import OrderSerializer, CheckoutSerializer


class CheckoutView(generics.CreateAPIView):
    """POST /checkout/  body: {"address_id": <id>, "coupon_code": "SAVE20" (optional)}"""
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        # Respond with the full, read-only Order representation
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """GET /orders/ - the current user's own order history, newest first."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related('items')
            .order_by('-created_at')
        )


class OrderDetailView(generics.RetrieveAPIView):
    """GET /orders/<id>/ - scoped to the current user's own orders (404, not 403, for others')."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderCancelView(generics.GenericAPIView):
    """
    POST /orders/<id>/cancel/  - only while status is pending or processing
    (agreed rule: once it's shipped, a simple flag can't recall a package
    already in transit - that needs a real logistics/support process).

    On success: restores stock for every item, reverses coupon usage
    (deletes the CouponUsage row and decrements used_count) so the user
    can use that coupon again, and marks the order cancelled. All in one
    transaction, with the same stock-locking approach as checkout.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        order = self.get_object()

        if order.status == Order.STATUS_CANCELLED :
            raise ValidationError({
                "detail": "This order is already cancelled."
            })
        
        if order.status not in (Order.STATUS_PENDING, Order.STATUS_PROCESSING):
            raise ValidationError({
                "detail": "Only pending or processing orders can be cancelled."
            })

        with transaction.atomic():
            items = list(order.items.all())
            variant_ids = [i.variant_id for i in items if i.variant_id]
            locked_variants = {
                v.id: v for v in
                ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
            }

            for item in items:
                variant = locked_variants.get(item.variant_id)
                if variant is not None:
                    variant.stock += item.quantity
                    variant.save(update_fields=['stock'])
                # if variant is None, the product/variant was deleted since -
                # nothing left to restore stock to, the OrderItem snapshot
                # is the only record left and that's fine.

            usage = getattr(order, 'coupon_usage', None)
            if usage is not None:
                coupon = usage.coupon
                usage.delete()
                if coupon.used_count > 0:
                    coupon.used_count -= 1
                    coupon.save(update_fields=['used_count'])

            order.status = Order.STATUS_CANCELLED
            order.save(update_fields=['status'])

        return Response(OrderSerializer(order).data)
