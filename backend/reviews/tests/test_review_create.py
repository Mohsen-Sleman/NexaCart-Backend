import pytest
from django.urls import reverse
from rest_framework import status
from orders.models import Order
from products.factories import ProductFactory, ProductVariantFactory
from reviews.models import Review
from users.factories import UserFactory
from .helpers import give_user_an_order_containing

pytestmark = pytest.mark.django_db

CREATE_URL = reverse('review-create')


def test_create_requires_authentication(api_client):
    product = ProductFactory()
    response = api_client.post(CREATE_URL, {'product': product.id, 'rating': 5})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_rejected_never_purchased(auth_client):
    user = UserFactory()
    product = ProductFactory()

    response = auth_client(user).post(CREATE_URL, {'product': product.id, 'rating': 5})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'purchased' in str(response.data).lower()


@pytest.mark.parametrize('not_yet_status', [Order.STATUS_PENDING, Order.STATUS_PROCESSING, Order.STATUS_SHIPPED])
def test_create_rejected_order_not_delivered_yet(auth_client, not_yet_status):
    user = UserFactory()
    variant = ProductVariantFactory()
    give_user_an_order_containing(user, variant, status=not_yet_status)

    response = auth_client(user).post(CREATE_URL, {'product': variant.product.id, 'rating': 5})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'delivered' in str(response.data).lower()


def test_create_cancelled_order_counts_as_never_purchased(auth_client):
    """
    A cancelled order shouldn't grant review eligibility, and the message
    should match 'never purchased', not 'wait for delivery' - the two
    give different advice to the user.
    """
    user = UserFactory()
    variant = ProductVariantFactory()
    give_user_an_order_containing(user, variant, status=Order.STATUS_CANCELLED)

    response = auth_client(user).post(CREATE_URL, {'product': variant.product.id, 'rating': 5})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'purchased' in str(response.data).lower()


def test_create_success_after_delivered_order(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory()
    give_user_an_order_containing(user, variant, status=Order.STATUS_DELIVERED)

    response = auth_client(user).post(
        CREATE_URL, {'product': variant.product.id, 'rating': 4, 'comment': 'Nice!'}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert Review.objects.filter(user=user, product=variant.product).exists()


def test_create_rejected_duplicate_review(auth_client):
    user = UserFactory()
    variant = ProductVariantFactory()
    give_user_an_order_containing(user, variant, status=Order.STATUS_DELIVERED)
    client = auth_client(user)
    client.post(CREATE_URL, {'product': variant.product.id, 'rating': 5})

    response = client.post(CREATE_URL, {'product': variant.product.id, 'rating': 3})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'already reviewed' in str(response.data).lower()
    assert Review.objects.filter(user=user, product=variant.product).count() == 1


@pytest.mark.parametrize('bad_rating', [0, 6, -1])
def test_create_rejected_invalid_rating(auth_client, bad_rating):
    user = UserFactory()
    variant = ProductVariantFactory()
    give_user_an_order_containing(user, variant, status=Order.STATUS_DELIVERED)

    response = auth_client(user).post(
        CREATE_URL, {'product': variant.product.id, 'rating': bad_rating}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_response_shows_reviewer_name_not_email(auth_client):
    user = UserFactory(first_name='Jane', last_name='Doe')
    variant = ProductVariantFactory()
    give_user_an_order_containing(user, variant, status=Order.STATUS_DELIVERED)

    response = auth_client(user).post(CREATE_URL, {'product': variant.product.id, 'rating': 5})

    assert response.data['reviewer_name'] == 'Jane D.'
    assert 'email' not in response.data
