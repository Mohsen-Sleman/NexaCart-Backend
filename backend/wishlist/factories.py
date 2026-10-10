import factory
from factory.django import DjangoModelFactory
from .models import Wishlist, WishlistItem
from users.factories import UserFactory
from products.factories import ProductFactory


class WishlistFactory(DjangoModelFactory):
    class Meta:
        model = Wishlist
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)


class WishlistItemFactory(DjangoModelFactory):
    class Meta:
        model = WishlistItem

    wishlist = factory.SubFactory(WishlistFactory)
    product = factory.SubFactory(ProductFactory)
