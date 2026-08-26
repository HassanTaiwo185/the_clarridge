from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import TeamMember
from .serializers import TeamMemberSerializer
from common.permissions import IsAdminOrSuperUserOrReadOnly


class TeamMemberListCreateView(generics.ListCreateAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrSuperUserOrReadOnly()]
        return [AllowAny()]


class TeamMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAdminOrSuperUserOrReadOnly]
