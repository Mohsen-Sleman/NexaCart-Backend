from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Moderation only: staff can read and delete a review (e.g. abusive
    text), but not rewrite what a customer said or fabricate one.
    """
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('product__name', 'user__email', 'comment')
    readonly_fields = ('user', 'product', 'rating', 'comment', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False
