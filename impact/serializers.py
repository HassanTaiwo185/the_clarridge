from rest_framework import serializers
from .models import ImpactStats


class ImpactStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactStats
        fields = ['students_reached', 'universities', 'updated_at']