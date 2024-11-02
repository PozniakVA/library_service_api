from datetime import timedelta

from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from books_service.models import Book
from borrowings_service.models import Borrowing
from borrowings_service.serializer import (
    BorrowingSerializer,
    BorrowingDetailSerializer,
    BorrowingListSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)
from notifications_service.tasks import (
    send_return_borrowing_success,
    send_borrowing_success,
    reminder_to_return_the_book_in_one_day,
    reminder_to_return_the_book,
)
from payments_service.views import pay_payment


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.select_related().prefetch_related("payments")

    reminders = []

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        if self.action == "borrowing_return":
            return BorrowingReturnSerializer
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):

        if request.user.payments.filter(status="PENDING"):
            return Response(
                {"detail": "Pay previous borrowings first"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book = get_object_or_404(Book, id=request.data["book"])

        if book.inventory < 1:
            return Response(
                {"detail": "The copies of this book are not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        borrowing = serializer.instance

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

        return pay_payment(request, serializer.instance.id)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        queryset = self.queryset
        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")

        option = {"true": True, "false": False}
        if is_active in option:
            queryset = queryset.filter(
                actual_return_date__isnull=option[is_active]
            )

        if user_id and self.request.user.is_staff:
            queryset = queryset.filter(user__id=int(user_id))

        return queryset.order_by("borrow_date")

    @extend_schema(
        request=BorrowingReturnSerializer,
        responses={
            status.HTTP_200_OK: {"description": "Book returned successfully!"},
            status.HTTP_400_BAD_REQUEST: {
                "description": "Book already returned!"
            },
        },
        description="Action that returns the books,"
                    " сan also render the fine payment page"
                    " if the book is returned late than expected",
        methods=["POST"]
    )
    @action(detail=True, methods=["post"], url_path="return")
    def borrowing_return(self, request, pk=None):
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                description="Filter by actual_return_date "
                            "(ex. ?is_active=true)",
            ),
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                description="Filter by user_id (ex. ?user_id=7),"
                            " only for admin",
            )
        ]
    )
    def list(self, request):
        return super().list(request)
