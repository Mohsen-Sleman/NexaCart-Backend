from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from products.models import Product


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews'
    )
    # Reviews attach to the Product, not the Variant: a customer rates
    # "the iPhone 15", not "the 128GB one".
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # DB-enforced: one review per user per product.
            models.UniqueConstraint(fields=['user', 'product'], name='unique_review_per_user_product')
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.product.name} ({self.rating}/5)"
