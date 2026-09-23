from django.contrib import admin
from .models import (
    Category, Product, ProductImage, ProductAttribute,
    ProductVariant, VariantAttribute,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('sku', 'price', 'stock', 'is_active')
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'is_active', 'created_at')
    list_filter = ('category', 'brand', 'is_active')
    search_fields = ('name', 'slug', 'brand')
    inlines = [ProductAttributeInline, ProductImageInline, ProductVariantInline]


class VariantAttributeInline(admin.TabularInline):
    model = VariantAttribute
    extra = 1


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Registered on its own (not just as an inline) so a variant's own
    change page can host its VariantAttribute inline - e.g. Color: Red,
    Size: L for that specific SKU.
    """
    list_display = ('sku', 'product', 'price', 'stock', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('sku', 'product__name')
    inlines = [VariantAttributeInline]