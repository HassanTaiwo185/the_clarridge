from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'slug',
            'author_name',
            'summary',
            'pdf_file',
            'date_written',
            'date_posted',
            'uploaded_by',
            'uploaded_by_username',
        ]
        read_only_fields = ['id', 'slug', 'date_posted', 'uploaded_by']

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)