from rest_framework import serializers

from payments_service.models import Payments


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payments
        fields = [
            "id",
            "borrowing",
            "session_id",
            "session_url",
            "status",
            "type",
            "crated_at",
            "total_price",
        ]
        read_only_fields = ["id", "crated_at"]


class PaymentListSerializer(PaymentSerializer):
    borrowing = serializers.SlugRelatedField(
        slug_field="book__title",
        read_only=True
    )
