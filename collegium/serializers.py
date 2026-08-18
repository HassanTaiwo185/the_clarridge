from rest_framework import serializers
from .models import CollegiumMember


class CollegiumMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollegiumMember
        fields = ['id', 'member_name', 'photo', 'school', 'field']
        read_only_fields = ['id']