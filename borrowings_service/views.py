from datetime import timedelta

from django.shortcuts import render
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
    BorrowingsReturnSerializer,
)
from notifications_service.tasks import (
    send_return_borrowing_success,
    send_borrowing_success,
    reminder_to_return_the_book_in_one_day,
    reminder_to_return_the_book,
)
from payments_service.views import stripe_payment


class BorrowingsViewSet(viewsets.ModelViewSet):
    queryset = Borrowings.objects.select_related()
    permission_classes = [IsAuthenticated]

    reminders = []

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
                {"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        borrowing = serializer.instance

        if book.inventory > 0:
            book.inventory -= 1
            book.save()

            send_borrowing_success.delay(request.user.id, borrowing.book.title)

            expected_date = borrowing.expected_return_date
            before_expected_date = expected_date - timedelta(days=1)
            if before_expected_date >= timezone.now():
                reminder_in_advance = (
                    reminder_to_return_the_book_in_one_day.apply_async(
                        (request.user.id, borrowing.book.title),
                        eta=before_expected_date,
                    )
                )
                self.reminders.append(reminder_in_advance)

            reminder_at_the_end = reminder_to_return_the_book.apply_async(
                (request.user.id, borrowing.book.title),
                eta=expected_date,
            )

            self.reminders.append(reminder_at_the_end)

            return stripe_payment(request, serializer.instance.id)

        return Response(
            {"detail": "The copies of this book are not available."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        queryset = self.queryset
        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")

        option = {"True": True, "False": False}
        if is_active in option:
            queryset = queryset.filter(
                actual_return_date__isnull=option[is_active]
            )

        if user_id and self.request.user.is_staff:
            queryset = queryset.filter(user__id=int(user_id))

        return queryset.order_by("expected_return_date")

    @action(detail=True, methods=["post"], url_path="return")
    def borrowings_return(self, request, pk=None):
        borrowing = self.get_object()

        if not borrowing.actual_return_date:

            borrowing.actual_return_date = timezone.now()
            borrowing.book.inventory += 1
            borrowing.book.save()
            borrowing.save()

            for reminder in self.reminders:
                reminder.revoke()

            send_return_borrowing_success.delay(
                request.user.id,
                borrowing.book.title
            )

            if borrowing.actual_return_date > borrowing.expected_return_date:
                return render(
                    request,
                    "payments_service/fine_page.html",
                    context={"context": borrowing}
                )

            return Response(
                {"detail": "Book returned successfully!"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Book already returned!"},
            status=status.HTTP_400_BAD_REQUEST
        )
