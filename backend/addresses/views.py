from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Address
from .serializers import AddressSerializer


class AddressListCreateView(generics.ListCreateAPIView):
    """
    GET  /addresses/  - the current user's own addresses only.
    POST /addresses/  - create a new one (auto-becomes default if it's the
                        user's first address - see Address.save()).
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /addresses/<id>/ - scoped to the current user's own
    addresses (get_queryset), so someone else's address ID 404s instead
    of 403 - same reasoning as CartItem.

    Setting is_default via PATCH just works through the normal serializer -
    Address.save() takes care of un-setting the previous default.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response(
                {"detail": "Cannot delete your default address. "
                        "Set a different address as default first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
