from rest_framework import serializers

from books_service.serializer import BookSerializer
from borrowings_service.models import Borrowings
from payments_service.serializer import PaymentListSerializer, PaymentSerializerInBorrowings
from users_service.serializer import UserSerializer


class BorrowingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowings
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        ]
        read_only_fields = ["id", "user", "borrow_date", "actual_return_date"]


class BorrowingsListSerializer(BorrowingsSerializer):
    book = serializers.SlugRelatedField(slug_field="title", read_only=True)
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)
    payments = PaymentSerializerInBorrowings(many=True, read_only=True)

    class Meta(BorrowingsSerializer.Meta):
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        ]


class BorrowingsDetailSerializer(BorrowingsSerializer):
    payments = PaymentListSerializer(many=True, read_only=True)
    book = BookSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta(BorrowingsSerializer.Meta):
        fields = BorrowingsSerializer.Meta.fields


class BorrowingsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowings
        fields = ["expected_return_date", "book"]


class BorrowingsReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowings
        fields = []
