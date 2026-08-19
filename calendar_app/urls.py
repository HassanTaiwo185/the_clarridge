from django.urls import path
from .views import CalendarEventListCreateView, CalendarEventDetailView

urlpatterns = [
    path('', CalendarEventListCreateView.as_view(), name='calendar-event-list-create'),
    path('<int:pk>/', CalendarEventDetailView.as_view(), name='calendar-event-detail'),
]