import factory
from factory.django import DjangoModelFactory
from .models import Cart, CartItem
from users.factories import UserFactory
from products.factories import ProductVariantFactory


class CartFactory(DjangoModelFactory):
    class Meta:
        model = Cart
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)


class CartItemFactory(DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 1
