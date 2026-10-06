import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

User = get_user_model()

DEFAULT_PASSWORD = 'TestPass123!'


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)
        # Our password post_generation hook below already calls self.save()
        # explicitly - without this, factory_boy ALSO saves again
        # afterwards (redundant double save, and the thing this warning
        # is about).
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone = factory.Sequence(lambda n: f'+96390000{n:04d}')
    is_verified = True
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        # UserFactory() -> password is DEFAULT_PASSWORD
        # UserFactory(password='Something123!') -> that instead
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()


class UnverifiedUserFactory(UserFactory):
    """A user who registered but hasn't confirmed their OTP yet."""
    is_verified = False


class StaffUserFactory(UserFactory):
    is_staff = True
    is_superuser = True