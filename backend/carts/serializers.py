from rest_framework import serializers
from .models import Cart, CartItem
from products.models import ProductVariant


class CartItemSerializer(serializers.ModelSerializer):
    """Read representation - flattens the info the frontend needs to render a cart row."""
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    unit_price = serializers.DecimalField(
        source="variant.price", max_digits=10, decimal_places=2, read_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'variant', 'product_name', 'sku',
            'unit_price', 'quantity', 'subtotal',
        ]
        read_only_fields = ['id', 'variant']

    def get_subtotal(self, obj):
        return obj.variant.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total']

    def get_total(self, obj):
        return sum((item.variant.price * item.quantity for item in obj.items.all()), 0)


class AddCartItemSerializer(serializers.Serializer):
    """
    Write-only input for POST /cart/items/. Not a ModelSerializer because the
    create logic isn't a plain insert - it has to check for an existing row
    for the same variant and add to its quantity instead (agreed behavior).
    """
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)

    def save(self, **kwargs):
        cart = kwargs['cart']
        variant = self.validated_data['variant']
        quantity = self.validated_data['quantity']

        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=['quantity'])
        return item


class UpdateCartItemSerializer(serializers.ModelSerializer):
    """Write-only input for PATCH /cart/items/<id>/ - sets the exact quantity."""
    class Meta:
        model = CartItem
        fields = ['quantity']
