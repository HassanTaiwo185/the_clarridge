from django.urls import path
from .views import CollegiumMemberListCreateView, CollegiumMemberDetailView

urlpatterns = [
    path('', CollegiumMemberListCreateView.as_view(), name='collegium-list-create'),
    path('<int:pk>/', CollegiumMemberDetailView.as_view(), name='collegium-detail'),
]