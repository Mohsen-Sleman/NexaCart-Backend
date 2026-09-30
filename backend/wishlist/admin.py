from django.contrib import admin
from .models import Wishlist, WishlistItem


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ('product', 'created_at')
    can_delete = False


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Read-only, same reasoning as Cart: fully managed by the user via the API."""
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__email',)
    inlines = [WishlistItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
