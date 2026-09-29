from django.urls import path
from .views import ProductReviewListView, ReviewCreateView, ReviewDetailView

urlpatterns = [
    path('products/<slug:slug>/reviews/', ProductReviewListView.as_view(), name='product-review-list'),
    path('reviews/', ReviewCreateView.as_view(), name='review-create'),
    path('reviews/<int:pk>/', ReviewDetailView.as_view(), name='review-detail'),
]
