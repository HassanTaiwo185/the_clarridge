from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import CollegiumMember
from .serializers import CollegiumMemberSerializer
from common.permissions import IsAdminOrSuperUserOrReadOnly


class CollegiumMemberListCreateView(generics.ListCreateAPIView):
    queryset = CollegiumMember.objects.all()
    serializer_class = CollegiumMemberSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrSuperUserOrReadOnly()]
        return [AllowAny()]


class CollegiumMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CollegiumMember.objects.all()
    serializer_class = CollegiumMemberSerializer
    permission_classes = [IsAdminOrSuperUserOrReadOnly]