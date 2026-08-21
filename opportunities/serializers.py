from rest_framework import serializers
from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ['id', 'title', 'slug', 'category', 'deadline', 'description', 'details_url']
        read_only_fields = ['id', 'slug']