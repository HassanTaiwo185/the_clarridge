from django.urls import path
from .views import TeamMemberListCreateView, TeamMemberDetailView

urlpatterns = [
    path('', TeamMemberListCreateView.as_view(), name='team-list-create'),
    path('<int:pk>/', TeamMemberDetailView.as_view(), name='team-detail'),
]