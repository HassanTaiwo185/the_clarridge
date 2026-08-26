from django.urls import path
from .views import ObservatoryPostListCreateView, ObservatoryPostDetailView

urlpatterns = [
    path('', ObservatoryPostListCreateView.as_view(), name='observatory-list-create'),
    path('<slug:slug>/', ObservatoryPostDetailView.as_view(), name='observatory-detail'),
]