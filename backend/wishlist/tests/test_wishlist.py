import pytest
from django.urls import reverse
from rest_framework import status
from wishlist.models import Wishlist, WishlistItem
from wishlist.factories import WishlistItemFactory
from products.factories import ProductFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

WISHLIST_URL = reverse('wishlist-detail')
ADD_ITEM_URL = reverse('wishlist-item-create')


def item_delete_url(item_id):
    return reverse('wishlist-item-delete', kwargs={'pk': item_id})


# -------------------------------------------------------------------- get
def test_get_requires_authentication(api_client):
    response = api_client.get(WISHLIST_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_creates_it_lazily(auth_client):
    user = UserFactory()
    assert Wishlist.objects.filter(user=user).exists() is False

    response = auth_client(user).get(WISHLIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert Wishlist.objects.filter(user=user).exists() is True


def test_get_shows_own_items_only(auth_client):
    me = UserFactory()
    someone_else = UserFactory()
    WishlistItemFactory(wishlist__user=me, product__name='Mine')
    WishlistItemFactory(wishlist__user=someone_else, product__name='NotMine')

    response = auth_client(me).get(WISHLIST_URL)

    names = [i['product_name'] for i in response.data['items']]
    assert names == ['Mine']


# ------------------------------------------------------------------- add
def test_add_requires_authentication(api_client):
    product = ProductFactory()
    response = api_client.post(ADD_ITEM_URL, {'product': product.id})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_add_new_product_returns_201(auth_client):
    user = UserFactory()
    product = ProductFactory()

    response = auth_client(user).post(ADD_ITEM_URL, {'product': product.id})

    assert response.status_code == status.HTTP_201_CREATED
    assert WishlistItem.objects.filter(wishlist__user=user, product=product).exists()


def test_add_creates_wishlist_lazily(auth_client):
    user = UserFactory()
    product = ProductFactory()
    assert Wishlist.objects.filter(user=user).exists() is False

    auth_client(user).post(ADD_ITEM_URL, {'product': product.id})

    assert Wishlist.objects.filter(user=user).exists() is True


def test_add_same_product_twice_is_idempotent(auth_client):
    """Agreed behavior: like a ❤ toggle - adding twice is not an error and
    doesn't duplicate the row, and the SECOND call returns 200, not 201."""
    user = UserFactory()
    product = ProductFactory()
    client = auth_client(user)

    first = client.post(ADD_ITEM_URL, {'product': product.id})
    second = client.post(ADD_ITEM_URL, {'product': product.id})

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_200_OK
    assert WishlistItem.objects.filter(wishlist__user=user, product=product).count() == 1


def test_add_rejects_inactive_product(auth_client):
    user = UserFactory()
    product = ProductFactory(is_active=False)

    response = auth_client(user).post(ADD_ITEM_URL, {'product': product.id})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_add_rejects_unknown_product(auth_client):
    user = UserFactory()
    response = auth_client(user).post(ADD_ITEM_URL, {'product': 999999})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------- remove
def test_remove_requires_authentication(api_client):
    item = WishlistItemFactory()
    response = api_client.delete(item_delete_url(item.id))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_remove_own_item_success(auth_client):
    user = UserFactory()
    item = WishlistItemFactory(wishlist__user=user)

    response = auth_client(user).delete(item_delete_url(item.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert WishlistItem.objects.filter(pk=item.pk).exists() is False


def test_remove_someone_elses_item_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    item = WishlistItemFactory(wishlist__user=owner)

    response = auth_client(attacker).delete(item_delete_url(item.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert WishlistItem.objects.filter(pk=item.pk).exists() is True
