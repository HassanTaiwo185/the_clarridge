from rest_framework import serializers
from .models import ObservatoryPost


class ObservatoryPostSerializer(serializers.ModelSerializer):
    posted_by_username = serializers.CharField(source='posted_by.username', read_only=True)

    class Meta:
        model = ObservatoryPost
        fields = [
            'id', 'title', 'slug', 'category', 'summary', 'content',
            'cover_image', 'read_time_minutes', 'is_featured',
            'posted_by', 'posted_by_username', 'date_posted',
        ]
        read_only_fields = ['id', 'slug', 'posted_by', 'date_posted']