from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Opportunity
from .serializers import OpportunitySerializer
from common.permissions import IsAdminOrSuperUserOrReadOnly


class OpportunityListCreateView(generics.ListCreateAPIView):
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrSuperUserOrReadOnly()]
        return [AllowAny()]


class OpportunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer
    lookup_field = 'slug'
    permission_classes = [IsAdminOrSuperUserOrReadOnly]