from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from books_service.models import Book
from borrowings_service.models import Borrowings
from borrowings_service.serializer import (
    BorrowingsSerializer,
    BorrowingsDetailSerializer,
    BorrowingsListSerializer,
    BorrowingsCreateSerializer,
    BorrowingsReturnSerializer
)


class BorrowingsViewSet(viewsets.ModelViewSet):
    queryset = Borrowings.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingsListSerializer
        if self.action == "retrieve":
            return BorrowingsDetailSerializer
        if self.action == "borrowings_return":
            return BorrowingsReturnSerializer
        if self.action == "create":
            return BorrowingsCreateSerializer
        return BorrowingsSerializer

    def create(self, request, *args, **kwargs):

        try:
            book = Book.objects.get(id=request.data["book"])
        except Book.DoesNotExist:
            return Response(
                {"detail": "Book not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        if book.inventory > 0:
            book.inventory -= 1
            book.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        return Response(
            {"detail": "The copies of this book are not available."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="return")
    def borrowings_return(self, request, pk=None):
        borrowing = self.get_object()

        if not borrowing.actual_return_date:

            borrowing.actual_return_date = timezone.now()
            borrowing.book.inventory += 1
            borrowing.save()
            return Response(
                {"detail": "Book returned successfully!"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Book already returned!"},
            status=status.HTTP_400_BAD_REQUEST
        )

