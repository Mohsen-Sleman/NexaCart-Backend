from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import (
    CartSerializer, CartItemSerializer,
    AddCartItemSerializer, UpdateCartItemSerializer,
)


class CartDetailView(generics.RetrieveAPIView):
    """GET /cart/ - the current user's cart, created lazily if it doesn't exist yet."""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart


class CartItemCreateView(generics.CreateAPIView):
    """
    POST /cart/items/  body: {"variant": <id>, "quantity": <int>}
    Adds a new line, or increases the quantity if that variant is
    already in the cart (agreed behavior).
    """
    serializer_class = AddCartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        item = serializer.save(cart=cart)

        # Respond with the full, friendlier read representation
        # (product name, subtotal, etc.), not the bare write input.
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class CartItemUpdateDeleteView(generics.UpdateAPIView, generics.DestroyAPIView):
    """
    PATCH  /cart/items/<id>/  body: {"quantity": <int>} - sets the exact quantity.
    DELETE /cart/items/<id>/  - removes the line entirely.
    """
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'delete', 'head', 'options']

    def get_queryset(self):
        # Scoped to the current user's own cart only. An item that exists
        # but belongs to someone else correctly 404s instead of 403 -
        # we don't want to reveal that the item ID exists at all.
        return CartItem.objects.filter(cart__user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # Same idea as create: respond with the full read representation.
        instance = self.get_object()
        return Response(CartItemSerializer(instance).data)
