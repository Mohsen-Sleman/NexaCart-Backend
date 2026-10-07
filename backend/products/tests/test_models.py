import pytest
from django.db import IntegrityError
from products.factories import (
    CategoryFactory, ProductFactory, ProductImageFactory,
    ProductAttributeFactory, VariantAttributeFactory, ProductVariantFactory,
)
from products.models import Product, ProductAttribute, VariantAttribute

pytestmark = pytest.mark.django_db


# ------------------------------------------------------------------ slugs
def test_product_slug_auto_generated_from_name():
    product = ProductFactory(name='Air Runner 2024')
    assert product.slug == 'air-runner-2024'


def test_product_slug_collision_gets_suffixed():
    first = ProductFactory(name='T-Shirt')
    second = ProductFactory(name='T-Shirt')

    assert first.slug == 't-shirt'
    assert second.slug == 't-shirt-2'


def test_product_slug_three_way_collision():
    first = ProductFactory(name='T-Shirt')
    second = ProductFactory(name='T-Shirt')
    third = ProductFactory(name='T-Shirt')

    assert {first.slug, second.slug, third.slug} == {'t-shirt', 't-shirt-2', 't-shirt-3'}


def test_explicit_slug_is_respected_not_overwritten():
    product = ProductFactory(name='Some Product', slug='custom-slug')
    assert product.slug == 'custom-slug'


def test_category_slug_auto_generated():
    category = CategoryFactory(name='Home & Kitchen')
    assert category.slug == 'home-kitchen'


# ------------------------------------------------------------- is_primary
def test_first_image_can_be_primary():
    product = ProductFactory()
    image = ProductImageFactory(product=product, is_primary=True)
    assert image.is_primary is True


def test_second_primary_image_unsets_the_first():
    product = ProductFactory()
    first = ProductImageFactory(product=product, is_primary=True)
    second = ProductImageFactory(product=product, is_primary=True)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary is False
    assert second.is_primary is True


def test_primary_images_are_scoped_per_product_not_global():
    """Two different products each having their own primary image must not interfere."""
    image_a = ProductImageFactory(is_primary=True)  # product A, default factory
    image_b = ProductImageFactory(is_primary=True)  # product B, different product

    image_a.refresh_from_db()
    assert image_a.is_primary is True  # untouched by product B's image
    assert image_b.is_primary is True


def test_non_primary_image_does_not_disturb_existing_primary():
    product = ProductFactory()
    primary = ProductImageFactory(product=product, is_primary=True)
    ProductImageFactory(product=product, is_primary=False)

    primary.refresh_from_db()
    assert primary.is_primary is True


# ------------------------------------------------------- unique constraints
def test_product_attribute_key_unique_per_product():
    product = ProductFactory()
    ProductAttributeFactory(product=product, key='Material', value='Cotton')

    with pytest.raises(IntegrityError):
        ProductAttribute.objects.create(product=product, key='Material', value='Polyester')


def test_same_attribute_key_allowed_on_different_products():
    ProductAttributeFactory(product=ProductFactory(), key='Material', value='Cotton')
    # Must NOT raise - the uniqueness is per-product, not global.
    ProductAttributeFactory(product=ProductFactory(), key='Material', value='Leather')


def test_variant_attribute_key_unique_per_variant():
    variant = ProductVariantFactory()
    VariantAttributeFactory(variant=variant, key='Color', value='Black')

    with pytest.raises(IntegrityError):
        VariantAttribute.objects.create(variant=variant, key='Color', value='White')
