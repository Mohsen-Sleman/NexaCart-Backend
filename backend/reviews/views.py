from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from products.models import Product
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer


class ProductReviewListView(generics.ListAPIView):
    """GET /products/<slug>/reviews/ - public, newest first."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        product = get_object_or_404(Product, slug=self.kwargs['slug'], is_active=True)
        return (
            Review.objects.filter(product=product)
            .select_related('user')
            .order_by('-created_at')
        )


class ReviewCreateView(generics.CreateAPIView):
    """POST /reviews/  body: {"product": <id>, "rating": 1-5, "comment": "..."}"""
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /reviews/<id>/ - scoped to the current user's own
    reviews, so someone else's review id 404s (same pattern as cart items,
    addresses and orders).
    """
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).select_related('user')

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ReviewUpdateSerializer
        return ReviewSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(ReviewSerializer(self.get_object()).data)
