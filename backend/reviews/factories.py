import factory
from factory.django import DjangoModelFactory
from .models import Review
from users.factories import UserFactory
from products.factories import ProductFactory


class ReviewFactory(DjangoModelFactory):
    class Meta:
        model = Review
        django_get_or_create = ('user', 'product')

    user = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory)
    rating = 5
    comment = 'Great product!'
