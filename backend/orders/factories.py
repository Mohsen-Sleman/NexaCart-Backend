import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from .models import Order, OrderItem
from users.factories import UserFactory
from products.factories import ProductVariantFactory


class OrderFactory(DjangoModelFactory):
    """
    Builds an Order directly (bypassing checkout) - for tests that need an
    EXISTING order in a specific state (list/detail/cancel), not for
    testing checkout itself (that goes through the real endpoint).
    """
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = Order.STATUS_PENDING
    payment_method = 'cod'
    payment_status = Order.PAYMENT_UNPAID
    subtotal = Decimal('100.00')
    discount_amount = Decimal('0.00')
    shipping_fee = Decimal('5.00')
    total_amount = Decimal('105.00')
    full_name = 'Test Recipient'
    phone = '+963900000000'
    country = 'Syria'
    city = 'Damascus'
    street = 'Test Street'


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    product_name = factory.LazyAttribute(lambda o: o.variant.product.name)
    sku = factory.LazyAttribute(lambda o: o.variant.sku)
    unit_price = factory.LazyAttribute(lambda o: o.variant.price)
    quantity = 1
    subtotal = factory.LazyAttribute(lambda o: o.variant.price)
