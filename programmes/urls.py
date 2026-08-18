from django.urls import path
from .views import ProgrammeListCreateView, ProgrammeDetailView

urlpatterns = [
    path('', ProgrammeListCreateView.as_view(), name='programme-list-create'),
    path('<slug:slug>/', ProgrammeDetailView.as_view(), name='programme-detail'),
]