from django.urls import path
from .views import (
    TestimonialListCreateView,
    TestimonialDetailView,
    PublicApprovedTestimonialListView,
)

urlpatterns = [
    path('', TestimonialListCreateView.as_view(), name='testimonial-list-create'),
    path('<int:pk>/', TestimonialDetailView.as_view(), name='testimonial-detail'),
    path('public/', PublicApprovedTestimonialListView.as_view(), name='testimonial-public-list'),
]