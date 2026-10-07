import pytest
from django.urls import reverse
from rest_framework import status
from carts.models import CartItem
from carts.factories import CartItemFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


def item_url(item_id):
    return reverse('cart-item-update-delete', kwargs={'pk': item_id})


# ------------------------------------------------------------------ update
def test_update_requires_authentication(api_client):
    item = CartItemFactory(quantity=2)
    response = api_client.patch(item_url(item.id), {'quantity': 5})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_sets_absolute_value_not_additive(auth_client):
    """PATCH is NOT the same as POST /cart/items/ - it sets the number
    directly, it doesn't add on top of what's there."""
    user = UserFactory()
    item = CartItemFactory(cart__user=user, quantity=2)

    response = auth_client(user).patch(item_url(item.id), {'quantity': 7})

    assert response.status_code == status.HTTP_200_OK
    item.refresh_from_db()
    assert item.quantity == 7  # not 2 + 7 = 9


def test_update_can_decrease_quantity(auth_client):
    user = UserFactory()
    item = CartItemFactory(cart__user=user, quantity=5)

    response = auth_client(user).patch(item_url(item.id), {'quantity': 2})

    assert response.status_code == status.HTTP_200_OK
    item.refresh_from_db()
    assert item.quantity == 2


def test_update_quantity_cannot_go_to_zero(auth_client):
    user = UserFactory()
    item = CartItemFactory(cart__user=user, quantity=3)

    response = auth_client(user).patch(item_url(item.id), {'quantity': 0})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    item.refresh_from_db()
    assert item.quantity == 3  # unchanged


def test_update_someone_elses_item_returns_404_not_403(auth_client):
    """
    Scoped by cart__user in get_queryset - a real item id belonging to
    another user must look like it doesn't exist, not like it's merely
    forbidden (which would confirm the id is valid).
    """
    owner = UserFactory()
    attacker = UserFactory()
    item = CartItemFactory(cart__user=owner, quantity=2)

    response = auth_client(attacker).patch(item_url(item.id), {'quantity': 99})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    item.refresh_from_db()
    assert item.quantity == 2  # untouched


# ------------------------------------------------------------------ delete
def test_delete_requires_authentication(api_client):
    item = CartItemFactory()
    response = api_client.delete(item_url(item.id))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_success(auth_client):
    user = UserFactory()
    item = CartItemFactory(cart__user=user)

    response = auth_client(user).delete(item_url(item.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert CartItem.objects.filter(pk=item.pk).exists() is False


def test_delete_someone_elses_item_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    item = CartItemFactory(cart__user=owner)

    response = auth_client(attacker).delete(item_url(item.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert CartItem.objects.filter(pk=item.pk).exists() is True  # NOT deleted
