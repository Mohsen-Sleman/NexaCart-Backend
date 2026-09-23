from rest_framework import serializers
from .models import (
    Category, Product, ProductImage, ProductAttribute,
    ProductVariant, VariantAttribute,
)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'is_active']
        read_only_fields = ['id', 'slug']

class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['id', 'key', 'value']
        read_only_fields = ['id']

class VariantAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantAttribute
        fields = ['id', 'key', 'value']
        read_only_fields = ['id']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'alt_text', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    attributes = VariantAttributeSerializer(many=True, required=False)

    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'price', 'stock', 'is_active', 'attributes']
        read_only_fields = ['id']

    def create(self, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        variant = ProductVariant.objects.create(**validated_data)
        for attr in attributes_data:
            VariantAttribute.objects.create(variant=variant, **attr)
        return variant


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/browse endpoints (catalog pages)."""
    category = serializers.StringRelatedField()
    min_price = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'brand', 'category',
            'min_price', 'primary_image', 'is_active',
        ]

    def get_min_price(self, obj):
        active_variants = obj.variants.filter(is_active=True)
        cheapest = active_variants.order_by('price').first()
        return cheapest.price if cheapest else None

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first()
        if image:
            request = self.context.get('request')
            url = image.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full read serializer for a single product's page."""
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'name', 'slug', 'description', 'brand',
            'is_active', 'attributes', 'variants', 'images',
            'created_at', 'updated_at',
        ]


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Used for create/update by staff. A product must be created together with
    at least one variant - that's the only place price/stock/sku exist, so a
    product without a variant literally can't be sold.
    """
    attributes = ProductAttributeSerializer(many=True, required=False)
    variants = ProductVariantSerializer(many=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'name', 'description', 'brand',
            'is_active', 'attributes', 'variants',
        ]
        read_only_fields = ['id']

    def validate_variants(self, value):
        if not value:
            raise serializers.ValidationError(
                "A product must have at least one variant."
            )
        return value

    def create(self, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        variants_data = validated_data.pop('variants')

        product = Product.objects.create(**validated_data)

        for attr in attributes_data:
            ProductAttribute.objects.create(product=product, **attr)

        for variant_data in variants_data:
            variant_attrs = variant_data.pop('attributes', [])
            variant = ProductVariant.objects.create(product=product, **variant_data)
            for attr in variant_attrs:
                VariantAttribute.objects.create(variant=variant, **attr)

        return product

class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Used for UPDATE only. Deliberately excludes variants/attributes/images -
    those are edited individually through the Admin, not by re-sending the
    whole product.
    """
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'brand', 'is_active']