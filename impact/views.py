from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import ImpactStats
from .serializers import ImpactStatsSerializer
from common.permissions import IsAdminOrSuperUserOrReadOnly


class ImpactStatsView(generics.RetrieveUpdateAPIView):
    serializer_class = ImpactStatsSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAdminOrSuperUserOrReadOnly()]
        return [AllowAny()]

    def get_object(self):
        return ImpactStats.load()