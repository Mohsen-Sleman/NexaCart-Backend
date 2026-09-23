from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator


def generate_unique_slug(instance, source_field: str, slug_field: str = "slug"):
    """
    Builds a unique slug for `instance` from `source_field`.
    If the slugified value already exists on another row, appends
    -2, -3, ... until it's unique. Used by Category and Product.
    """
    base_slug = slugify(getattr(instance, source_field))
    slug = base_slug
    ModelClass = instance.__class__
    counter = 2

    qs = ModelClass.objects.filter(**{slug_field: slug})
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)

    while qs.exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
        qs = ModelClass.objects.filter(**{slug_field: slug})
        if instance.pk:
            qs = qs.exclude(pk=instance.pk)

    return slug


class Category(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, "name")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, "name")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)

    def __str__(self):
        return f"{self.product.name} image ({'primary' if self.is_primary else 'gallery'})"


class ProductAttribute(models.Model):
    """
    Descriptive key/value info about the product itself (e.g. Material: Cotton,
    Country of Origin: Turkey). NOT used to distinguish variants from each other -
    that's VariantAttribute's job.
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="attributes"
    )
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "key"], name="unique_product_attribute_key"
            )
        ]

    def __str__(self):
        return f"{self.product.name}: {self.key}={self.value}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} [{self.sku}]"


class VariantAttribute(models.Model):
    """
    The key/value pairs that actually DEFINE a variant and make it different
    from its siblings (e.g. Color: Red, Size: L). Standardized, case-consistent
    plain strings, per the project's stated requirement.
    """
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="attributes"
    )
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "key"], name="unique_variant_attribute_key"
            )
        ]

    def __str__(self):
        return f"{self.variant.sku}: {self.key}={self.value}"