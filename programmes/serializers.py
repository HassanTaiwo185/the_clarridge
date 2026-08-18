from rest_framework import serializers
from .models import Programme


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = [
            'id',
            'name',
            'slug',
            'status',
            'start_date',
            'end_date',
            'cover_image',
            'description',
        ]
        read_only_fields = ['id', 'slug']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        return attrs