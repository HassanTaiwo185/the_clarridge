from django.urls import path
from .views import ImpactStatsView

urlpatterns = [
    path('', ImpactStatsView.as_view(), name='impact-stats'),
]