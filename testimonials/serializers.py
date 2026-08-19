from rest_framework import serializers
from .models import Testimonial


class TestimonialSerializer(serializers.ModelSerializer):
    """Full serializer — used by admins, includes status."""

    class Meta:
        model = Testimonial
        fields = ['id', 'submitted_by', 'programme', 'content', 'status', 'submitted_at']
        read_only_fields = ['id', 'submitted_at']


class TestimonialCreateSerializer(serializers.ModelSerializer):
    """Public-facing: excludes `status`, always defaults to pending."""

    class Meta:
        model = Testimonial
        fields = ['submitted_by', 'programme', 'content']


class PublicTestimonialSerializer(serializers.ModelSerializer):
    """Public-facing read: only approved testimonials, no status field exposed."""

    class Meta:
        model = Testimonial
        fields = ['id', 'submitted_by', 'programme', 'content']