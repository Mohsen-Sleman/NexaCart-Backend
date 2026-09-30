from django.urls import path
from .views import WishlistDetailView, WishlistItemCreateView, WishlistItemDeleteView

urlpatterns = [
    path('wishlist/', WishlistDetailView.as_view(), name='wishlist-detail'),
    path('wishlist/items/', WishlistItemCreateView.as_view(), name='wishlist-item-create'),
    path('wishlist/items/<int:pk>/', WishlistItemDeleteView.as_view(), name='wishlist-item-delete'),
]
