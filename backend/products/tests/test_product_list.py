import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from products.factories import CategoryFactory, ProductFactory, ProductVariantFactory
from users.factories import StaffUserFactory, UserFactory

pytestmark = pytest.mark.django_db

PRODUCT_LIST_URL = reverse('product-list-create')


# --------------------------------------------------------------- visibility
def test_guest_only_sees_active_products(api_client):
    ProductFactory(name='Visible', is_active=True)
    ProductFactory(name='Hidden', is_active=False)

    response = api_client.get(PRODUCT_LIST_URL)

    names = [p['name'] for p in response.data]
    assert 'Visible' in names
    assert 'Hidden' not in names


def test_staff_sees_inactive_products_too(auth_client):
    staff = StaffUserFactory()
    ProductFactory(name='Hidden', is_active=False)

    response = auth_client(staff).get(PRODUCT_LIST_URL)

    names = [p['name'] for p in response.data]
    assert 'Hidden' in names


def test_regular_authenticated_user_does_not_see_inactive(auth_client):
    """Being logged in isn't enough - must specifically be staff."""
    regular_user = UserFactory()
    ProductFactory(name='Hidden', is_active=False)

    response = auth_client(regular_user).get(PRODUCT_LIST_URL)

    names = [p['name'] for p in response.data]
    assert 'Hidden' not in names


# ----------------------------------------------------------------- filters
def test_filter_by_category(api_client):
    electronics = CategoryFactory(name='Electronics')
    clothing = CategoryFactory(name='Clothing')
    ProductFactory(name='Phone', category=electronics)
    ProductFactory(name='Shirt', category=clothing)

    response = api_client.get(PRODUCT_LIST_URL, {'category': electronics.slug})

    names = [p['name'] for p in response.data]
    assert names == ['Phone']


def test_filter_by_brand(api_client):
    ProductFactory(name='Nike Shoe', brand='Nike')
    ProductFactory(name='Adidas Shoe', brand='Adidas')

    response = api_client.get(PRODUCT_LIST_URL, {'brand': 'Nike'})

    names = [p['name'] for p in response.data]
    assert names == ['Nike Shoe']


def test_filter_by_price_range(api_client):
    cheap = ProductFactory(name='Cheap')
    ProductVariantFactory(product=cheap, price='10.00')
    expensive = ProductFactory(name='Expensive')
    ProductVariantFactory(product=expensive, price='500.00')

    response = api_client.get(PRODUCT_LIST_URL, {'price_min': '5', 'price_max': '50'})

    names = [p['name'] for p in response.data]
    assert names == ['Cheap']


def test_filter_by_price_range_no_duplicates_with_multiple_variants(api_client):
    """A product with several variants inside the range must appear only once."""
    product = ProductFactory(name='Multi Variant')
    ProductVariantFactory(product=product, price='20.00')
    ProductVariantFactory(product=product, price='25.00')

    response = api_client.get(PRODUCT_LIST_URL, {'price_min': '10', 'price_max': '30'})

    names = [p['name'] for p in response.data]
    assert names.count('Multi Variant') == 1


def test_search_by_name(api_client):
    ProductFactory(name='iPhone 15')
    ProductFactory(name='Samsung Galaxy')

    response = api_client.get(PRODUCT_LIST_URL, {'search': 'iphone'})

    names = [p['name'] for p in response.data]
    assert names == ['iPhone 15']


# -------------------------------------------------------------- min_price
def test_min_price_is_cheapest_active_variant(api_client):
    product = ProductFactory()
    ProductVariantFactory(product=product, price='50.00')
    ProductVariantFactory(product=product, price='30.00')

    response = api_client.get(PRODUCT_LIST_URL)

    item = next(p for p in response.data if p['id'] == product.id)
    assert item['min_price'] == Decimal('30.00')


def test_min_price_ignores_inactive_variants(api_client):
    product = ProductFactory()
    ProductVariantFactory(product=product, price='30.00', is_active=False)
    ProductVariantFactory(product=product, price='80.00', is_active=True)

    response = api_client.get(PRODUCT_LIST_URL)

    item = next(p for p in response.data if p['id'] == product.id)
    assert item['min_price'] == Decimal('80.00')  # not the cheaper, inactive one


# --------------------------------------------------- avg_rating / review_count
def test_avg_rating_and_review_count(api_client):
    from reviews.models import Review
    from users.factories import UserFactory as _UserFactory

    product = ProductFactory()
    Review.objects.create(user=_UserFactory(), product=product, rating=4)
    Review.objects.create(user=_UserFactory(), product=product, rating=2)

    response = api_client.get(PRODUCT_LIST_URL)

    item = next(p for p in response.data if p['id'] == product.id)
    assert item['review_count'] == 2
    assert item['avg_rating'] == 3.0  # (4 + 2) / 2


def test_avg_rating_is_null_with_no_reviews(api_client):
    product = ProductFactory()

    response = api_client.get(PRODUCT_LIST_URL)

    item = next(p for p in response.data if p['id'] == product.id)
    assert item['review_count'] == 0
    assert item['avg_rating'] is None
