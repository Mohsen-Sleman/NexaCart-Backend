from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from products.models import ProductVariant


class Cart(models.Model):
    """
    Created lazily by the Cart app itself (get_or_create on first access/add),
    never eagerly on user registration - keeps 'users' app fully unaware
    that carts exist at all.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "variant"], name="unique_cart_variant"
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.variant.sku} (cart #{self.cart_id})"
