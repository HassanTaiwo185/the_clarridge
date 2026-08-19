from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Testimonial
from .serializers import (
    TestimonialSerializer,
    TestimonialCreateSerializer,
    PublicTestimonialSerializer,
)
from .permissions import IsAdminOrSuperUserForManagement


class TestimonialListCreateView(generics.ListCreateAPIView):
    """
    GET: admin/superuser only — lists ALL testimonials (any status), for the review dashboard.
    POST: public — anyone can submit a testimonial (always starts as pending).
    """
    queryset = Testimonial.objects.all()
    permission_classes = [IsAdminOrSuperUserForManagement]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestimonialCreateSerializer
        return TestimonialSerializer


class TestimonialDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin-only: view, approve/reject (update status), or delete a single testimonial."""
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = [IsAdminOrSuperUserForManagement]


class PublicApprovedTestimonialListView(generics.ListAPIView):
    """Public: only approved testimonials, visible to everyone."""
    queryset = Testimonial.objects.filter(status=Testimonial.Status.APPROVED)
    serializer_class = PublicTestimonialSerializer
    permission_classes = [AllowAny]