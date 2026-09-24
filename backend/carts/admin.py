from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('variant', 'quantity', 'created_at', 'updated_at')
    can_delete = False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Read-only by design: carts are entirely managed by the user through the
    API. This view exists only so staff can look up a user's cart for
    support/debugging - not to edit it by hand.
    """
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__email',)
    inlines = [CartItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
