from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import CalendarEvent
from .serializers import CalendarEventSerializer
from common.permissions import IsAdminOrSuperUserOrReadOnly


class CalendarEventListCreateView(generics.ListCreateAPIView):
    queryset = CalendarEvent.objects.all()
    serializer_class = CalendarEventSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrSuperUserOrReadOnly()]
        return [AllowAny()]


class CalendarEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CalendarEvent.objects.all()
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAdminOrSuperUserOrReadOnly]