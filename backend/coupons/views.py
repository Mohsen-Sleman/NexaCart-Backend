from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .serializers import CouponPreviewSerializer


class CouponPreviewView(generics.GenericAPIView):
    """
    POST /coupons/preview/   body: {"code": "SAVE20"}

    Read-only: tells the user what a coupon WOULD do against their current
    cart, without creating anything or touching used_count. Deliberately
    does NOT check the per-user-once rule yet (needs Order/CouponUsage,
    added in the Orders stage) - so a coupon can preview as valid here and
    still get rejected at actual checkout if this user already used it.
    """
    serializer_class = CouponPreviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.coupon

        cart = getattr(request.user, 'cart', None)
        if not cart or not cart.items.exists():
            raise ValidationError({"detail": "Your cart is empty."})

        subtotal = sum(
            item.variant.price * item.quantity
            for item in cart.items.select_related('variant')
        )

        is_valid, reason = coupon.is_valid_for_amount(subtotal)
        if not is_valid:
            raise ValidationError({"detail": reason})

        discount = coupon.calculate_discount(subtotal)

        return Response({
            "code": coupon.code,
            "subtotal": str(subtotal),
            "discount_amount": str(discount),
            "total_after_discount": str(subtotal - discount),
        })
