import pytest
from django.urls import reverse
from rest_framework import status
from reviews.models import Review
from reviews.factories import ReviewFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


def review_url(review_id):
    return reverse('review-detail', kwargs={'pk': review_id})


def test_update_requires_authentication(api_client):
    review = ReviewFactory()
    response = api_client.patch(review_url(review.id), {'rating': 3})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_own_review_success(auth_client):
    user = UserFactory()
    review = ReviewFactory(user=user, rating=2, comment='Meh')

    response = auth_client(user).patch(review_url(review.id), {'rating': 5, 'comment': 'Actually great'})

    assert response.status_code == status.HTTP_200_OK
    review.refresh_from_db()
    assert review.rating == 5
    assert review.comment == 'Actually great'


def test_update_cannot_change_product(auth_client):
    user = UserFactory()
    review = ReviewFactory(user=user)
    original_product = review.product
    other_product = ReviewFactory().product

    auth_client(user).patch(review_url(review.id), {'product': other_product.id, 'rating': 4})

    review.refresh_from_db()
    assert review.product == original_product  # unchanged - not a field on ReviewUpdateSerializer


def test_update_someone_elses_review_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    review = ReviewFactory(user=owner, rating=5)

    response = auth_client(attacker).patch(review_url(review.id), {'rating': 1})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    review.refresh_from_db()
    assert review.rating == 5


def test_delete_requires_authentication(api_client):
    review = ReviewFactory()
    response = api_client.delete(review_url(review.id))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_own_review_success(auth_client):
    user = UserFactory()
    review = ReviewFactory(user=user)

    response = auth_client(user).delete(review_url(review.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Review.objects.filter(pk=review.pk).exists() is False


def test_delete_someone_elses_review_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    review = ReviewFactory(user=owner)

    response = auth_client(attacker).delete(review_url(review.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Review.objects.filter(pk=review.pk).exists() is True
