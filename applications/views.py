from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Application
from .serializers import ApplicationSerializer, ApplicationCreateSerializer
from .permissions import IsAdminOrSuperUserForManagement


class ApplicationListCreateView(generics.ListCreateAPIView):
    queryset = Application.objects.all()
    permission_classes = [IsAdminOrSuperUserForManagement]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ApplicationCreateSerializer
        return ApplicationSerializer


class ApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin-only: view, update status, or delete a single application."""
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAdminOrSuperUserForManagement]