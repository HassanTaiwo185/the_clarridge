from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Article
from .serializers import ArticleSerializer
from .permissions import IsOwnerOrSuperUserOrReadOnly


class ArticleListCreateView(generics.ListCreateAPIView):
    """
    GET: list all articles — open to everyone (AllowAny).
    POST: create a new article — must be authenticated.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsOwnerOrSuperUserOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: view a single article — open to everyone.
    PUT/PATCH/DELETE: only the uploader or a superuser.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'slug'
    permission_classes = [IsOwnerOrSuperUserOrReadOnly]