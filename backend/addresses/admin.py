from django.contrib import admin
from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'street', 'is_default', 'created_at')
    list_filter = ('is_default', 'country', 'city')
    search_fields = ('user__email', 'full_name', 'phone', 'city', 'street', 'postal_code')
