from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_order_confirmation_email(order_id):
    """
    Takes the order's id, not the Order instance itself (same reasoning as
    send_otp_email) - re-fetches fresh inside the worker process.
    """
    from .models import Order

    try:
        order = Order.objects.select_related('user').prefetch_related('items').get(pk=order_id)
    except Order.DoesNotExist:
        # Extremely unlikely (orders aren't hard-deleted), but a task
        # should never crash the worker over a race it can't control.
        return f"Order {order_id} no longer exists - skipping confirmation email."

    lines = [
        f"Hi {order.full_name},", "",
        f"Thanks for your order #{order.id}!", "",
        "Items:",
    ]
    for item in order.items.all():
        lines.append(f"  - {item.product_name} x{item.quantity} = {item.subtotal}")

    lines += [
        "",
        f"Subtotal: {order.subtotal}",
        f"Shipping: {order.shipping_fee}",
        f"Discount: -{order.discount_amount}",
        f"Total: {order.total_amount}",
        "",
        f"Shipping to: {order.street}, {order.city}, {order.country}",
        "",
        "Payment method: Cash on Delivery",
        "",
        "Thank you for shopping with NexaCart!",
    ]

    send_mail(
        subject=f"Order Confirmation - #{order.id}",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
    )
