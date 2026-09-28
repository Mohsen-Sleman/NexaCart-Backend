from django.contrib import admin
from .models import Order, OrderItem, CouponUsage


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ('variant', 'product_name', 'sku', 'unit_price', 'quantity', 'subtotal')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Staff can move an order through its lifecycle (status) and mark
    payment collected (payment_status) - that's the actual daily
    fulfillment workflow for a single-vendor store.
    """
    list_display = ('id', 'user', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status')
    search_fields = ('user__email', 'id')
    inlines = [OrderItemInline]

    readonly_fields = (
        'user', 'subtotal', 'discount_amount', 'shipping_fee', 'total_amount',
        'full_name', 'phone', 'country', 'city', 'street', 'building',
        'apartment', 'postal_code', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        # Orders are only ever created through checkout, never by hand.
        return False


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    """Read-only audit trail - this is a historical fact, not something to edit."""
    list_display = ('coupon', 'user', 'order', 'used_at')
    search_fields = ('coupon__code', 'user__email')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
