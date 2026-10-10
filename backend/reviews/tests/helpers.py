from decimal import Decimal
from orders.models import Order
from orders.factories import OrderFactory, OrderItemFactory


def give_user_an_order_containing(user, variant, status=Order.STATUS_DELIVERED):
    """Builds an order (any status) containing this variant, directly via
    the ORM - not through checkout, since these tests care about Review's
    eligibility check, not the checkout flow itself."""
    order = OrderFactory(user=user, status=status)
    OrderItemFactory(order=order, variant=variant, quantity=1)
    return order
