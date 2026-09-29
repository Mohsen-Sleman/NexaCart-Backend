from django.db import IntegrityError
from rest_framework import serializers
from orders.models import Order, OrderItem
from products.models import Product
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """Read representation. Shows a short display name, never the email."""
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'product', 'reviewer_name', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = fields

    def get_reviewer_name(self, obj):
        name = (obj.user.first_name or '').strip()
        last_initial = (obj.user.last_name or '').strip()[:1]
        if last_initial:
            name = f"{name} {last_initial}.".strip()
        return name or "Anonymous"


class ReviewCreateSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )

    class Meta:
        model = Review
        fields = ['product', 'rating', 'comment']

    def validate(self, attrs):
        user = self.context['request'].user
        product = attrs['product']

        # Purchase + delivery rule. Delivered order containing this product?
        delivered = OrderItem.objects.filter(
            order__user=user,
            order__status=Order.STATUS_DELIVERED,
            variant__product=product,
        ).exists()

        if not delivered:
            # Give a more helpful message depending on how close they are.
            in_progress = OrderItem.objects.filter(
                order__user=user, variant__product=product,
            ).exclude(order__status=Order.STATUS_CANCELLED).exists()
            
            if in_progress:
                raise serializers.ValidationError(
                    {"detail": "You can review this product once your order has been delivered."}
                )
            raise serializers.ValidationError(
                {"detail": "You can only review products you have purchased."}
            )

        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError(
                {"detail": "You have already reviewed this product. Edit your existing review instead."}
            )
        return attrs

    def create(self, validated_data):
        try:
            return Review.objects.create(user=self.context['request'].user, **validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"detail": "You have already reviewed this product."}
            )


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """The product can't be changed after the fact - only rating/comment."""
    class Meta:
        model = Review
        fields = ['rating', 'comment']
