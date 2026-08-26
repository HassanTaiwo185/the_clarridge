from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import ObservatoryPost
from .serializers import ObservatoryPostSerializer
from .permissions import IsOwnerOrSuperUserOrReadOnly


class ObservatoryPostListCreateView(generics.ListCreateAPIView):
    queryset = ObservatoryPost.objects.all()
    serializer_class = ObservatoryPostSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsOwnerOrSuperUserOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)


class ObservatoryPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ObservatoryPost.objects.all()
    serializer_class = ObservatoryPostSerializer
    lookup_field = 'slug'
    permission_classes = [IsOwnerOrSuperUserOrReadOnly]