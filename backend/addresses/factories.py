import factory
from factory.django import DjangoModelFactory
from .models import Address
from users.factories import UserFactory


class AddressFactory(DjangoModelFactory):
    class Meta:
        model = Address

    user = factory.SubFactory(UserFactory)
    country = 'Syria'
    city = 'Damascus'
    street = factory.Sequence(lambda n: f'Street {n}')
    full_name = 'Test Recipient'
    phone = factory.Sequence(lambda n: f'+96390000{n:04d}')
    is_default = False
