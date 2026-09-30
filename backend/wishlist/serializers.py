from rest_framework import serializers
from .models import Wishlist, WishlistItem
from products.models import Product


class WishlistItemSerializer(serializers.ModelSerializer):
    """Read representation - flattens what the frontend needs for a wishlist card."""
    product_name = serializers.CharField(source="product.name", read_only=True)
    slug = serializers.CharField(source="product.slug", read_only=True)
    min_price = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'product_name', 'slug', 'min_price', 'primary_image', 'created_at']
        read_only_fields = ['id', 'product', 'created_at']

    def get_min_price(self, obj):
        cheapest = obj.product.variants.filter(is_active=True).order_by('price').first()
        return cheapest.price if cheapest else None

    def get_primary_image(self, obj):
        image = obj.product.images.filter(is_primary=True).first()
        if not image:
            return None
        request = self.context.get('request')
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'items']


class AddWishlistItemSerializer(serializers.Serializer):
    """
    Write-only input for POST /wishlist/items/. Idempotent by design (agreed
    behavior): adding a product that's already there is not an error, it
    just stays there - matches how a ❤ toggle button behaves in real apps.
    """
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )

    def save(self, **kwargs):
        wishlist = kwargs['wishlist']
        product = self.validated_data['product']
        item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        self.created = created
        return item
