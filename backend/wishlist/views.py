from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Wishlist, WishlistItem
from .serializers import WishlistSerializer, WishlistItemSerializer, AddWishlistItemSerializer


class WishlistDetailView(generics.RetrieveAPIView):
    """GET /wishlist/ - the current user's wishlist, created lazily if it doesn't exist yet."""
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist


class WishlistItemCreateView(generics.CreateAPIView):
    """
    POST /wishlist/items/  body: {"product": <id>}
    Idempotent: 201 if newly added, 200 if it was already there - either
    way the response is the same item representation.
    """
    serializer_class = AddWishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        item = serializer.save(wishlist=wishlist)

        code = status.HTTP_201_CREATED if serializer.created else status.HTTP_200_OK
        return Response(WishlistItemSerializer(item, context={'request': request}).data, status=code)


class WishlistItemDeleteView(generics.DestroyAPIView):
    """DELETE /wishlist/items/<id>/ - scoped to the current user's own wishlist."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WishlistItem.objects.filter(wishlist__user=self.request.user)
