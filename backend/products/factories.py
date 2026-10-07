import factory
from factory.django import DjangoModelFactory
from .models import (
    Category, Product, ProductImage, ProductAttribute,
    ProductVariant, VariantAttribute,
)


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Category {n}')
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda n: f'Product {n}')
    brand = 'TestBrand'
    is_active = True


class ProductVariantFactory(DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    sku = factory.Sequence(lambda n: f'SKU-{n:05d}')
    price = '99.99'
    stock = 10
    is_active = True


class ProductAttributeFactory(DjangoModelFactory):
    class Meta:
        model = ProductAttribute

    product = factory.SubFactory(ProductFactory)
    key = 'Warranty'
    value = '1 Year'


class VariantAttributeFactory(DjangoModelFactory):
    class Meta:
        model = VariantAttribute

    variant = factory.SubFactory(ProductVariantFactory)
    key = 'Color'
    value = 'Black'


class ProductImageFactory(DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    image = factory.django.ImageField(filename='product.jpg', color='blue')
    is_primary = False
