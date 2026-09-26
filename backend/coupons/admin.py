from django.contrib import admin
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_type', 'discount_value', 'usage_limit',
        'used_count', 'is_active', 'start_date', 'end_date',
    )
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)
    readonly_fields = ('used_count',)
