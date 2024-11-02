from rest_framework import viewsets

from books_service.models import Book
from books_service.permissions import IsAdminUserOrReadOnly
from books_service.serializer import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = BookSerializer
