from rest_framework import serializers
from .models import Coupon


class CouponPreviewSerializer(serializers.Serializer):
    """
    Input only. Validates that the code exists; the actual eligibility
    (dates, usage limit, min order amount) is checked in the view, because
    it needs the cart's subtotal, which this serializer doesn't have access to.
    """
    code = serializers.CharField()

    def validate_code(self, value):
        try:
            self.coupon = Coupon.objects.get(code__iexact=value)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")
        return value
