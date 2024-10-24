from rest_framework import serializers

from books_service.serializer import BookSerializer
from borrowings_service.models import Borrowing
from payments_service.serializer import (
    PaymentListSerializer,
    PaymentSerializerInBorrowing
)
from users_service.serializer import UserSerializer


class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        ]
        read_only_fields = ["id", "user", "borrow_date", "actual_return_date"]


class BorrowingListSerializer(BorrowingSerializer):
    book = serializers.SlugRelatedField(slug_field="title", read_only=True)
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
    payments = PaymentSerializerInBorrowing(many=True, read_only=True)

    class Meta(BorrowingSerializer.Meta):
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        ]


class BorrowingDetailSerializer(BorrowingSerializer):
    payments = PaymentListSerializer(many=True, read_only=True)
    book = BookSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta(BorrowingSerializer.Meta):
        fields = BorrowingSerializer.Meta.fields


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ["expected_return_date", "book"]


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = []
