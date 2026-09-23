from django.db.models import Q
from rest_framework import generics, permissions
from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductWriteSerializer,
    ProductUpdateSerializer,
)
from .permissions import IsStaffOrReadOnly


class CategoryListView(generics.ListAPIView):
    """GET /categories/ - public, read-only. Managed through the Admin."""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductListCreateView(generics.ListCreateAPIView):
    """
    GET  /products/  - public catalog browsing, with filtering.
    POST /products/  - staff only, create a product with its first variant.
    """
    permission_classes = [IsStaffOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductWriteSerializer
        return ProductListSerializer

    def get_queryset(self):
        qs = Product.objects.select_related('category').prefetch_related('variants')

        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_active=True)

        return self._apply_filters(qs)

    def _apply_filters(self, qs):
        """
        filter by category, brand, min and max price 
        search by brand or product name
        """
        params = self.request.query_params

        category_slug = params.get('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        brand = params.get('brand')
        if brand:
            qs = qs.filter(brand__iexact=brand)

        price_min = params.get('price_min')
        price_max = params.get('price_max')
        if price_min:
            qs = qs.filter(variants__price__gte=price_min)
        if price_max:
            qs = qs.filter(variants__price__lte=price_max)
        if price_min or price_max:
            qs = qs.distinct()

        search = params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(brand__icontains=search))

        return qs


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /products/<slug>/  - public product detail page.
    PATCH  /products/<slug>/  - staff only, basic fields only (no variants).
    DELETE /products/<slug>/  - staff only.
    """
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = Product.objects.select_related('category').prefetch_related(
            'variants', 'variants__attributes', 'images', 'attributes'
        )
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_active=True)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ProductUpdateSerializer
        return ProductDetailSerializer