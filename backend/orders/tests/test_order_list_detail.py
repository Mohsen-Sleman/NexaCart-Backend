import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from orders.factories import OrderFactory
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

ORDER_LIST_URL = reverse('order-list')


def order_detail_url(order_id):
    return reverse('order-detail', kwargs={'pk': order_id})


# -------------------------------------------------------------------- list
def test_list_requires_authentication(api_client):
    response = api_client.get(ORDER_LIST_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_only_shows_own_orders(auth_client):
    me = UserFactory()
    someone_else = UserFactory()
    OrderFactory(user=me)
    OrderFactory(user=someone_else)

    response = auth_client(me).get(ORDER_LIST_URL)

    assert len(response.data) == 1


def test_list_newest_first(auth_client):
    user = UserFactory()
    older = OrderFactory(user=user)
    newer = OrderFactory(user=user)
    # auto_now_add ignores constructor kwargs - force distinct timestamps directly.
    type(older).objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(days=1))
    
    response = auth_client(user).get(ORDER_LIST_URL)

    assert response.data[0]['id'] == newer.id
    assert response.data[1]['id'] == older.id


# ------------------------------------------------------------------ detail
def test_detail_requires_authentication(api_client):
    order = OrderFactory()
    response = api_client.get(order_detail_url(order.id))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_detail_success(auth_client):
    user = UserFactory()
    order = OrderFactory(user=user)

    response = auth_client(user).get(order_detail_url(order.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data['id'] == order.id


def test_detail_someone_elses_order_returns_404(auth_client):
    owner = UserFactory()
    attacker = UserFactory()
    order = OrderFactory(user=owner)

    response = auth_client(attacker).get(order_detail_url(order.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
