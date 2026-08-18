from rest_framework import serializers
from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'id',
            'full_name',
            'email',
            'phone_number',
            'date_of_birth',
            'passport_photo',
            'cv_transcript',
            'status',
            'date_applied',
        ]
        read_only_fields = ['id', 'date_applied']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Public-facing: excludes `status`, so applicants can't set their own status."""

    class Meta:
        model = Application
        fields = [
            'full_name',
            'email',
            'phone_number',
            'date_of_birth',
            'passport_photo',
            'cv_transcript',
        ]