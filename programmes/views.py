from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Programme
from .serializers import ProgrammeSerializer
from .permissions import IsAdminOrSuperUserOrReadOnly


class ProgrammeListCreateView(generics.ListCreateAPIView):
    queryset = Programme.objects.all()
    serializer_class = ProgrammeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrSuperUserOrReadOnly()]
        return [AllowAny()]


class ProgrammeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Programme.objects.all()
    serializer_class = ProgrammeSerializer
    lookup_field = 'slug'
    permission_classes = [IsAdminOrSuperUserOrReadOnly]