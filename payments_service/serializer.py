from rest_framework import serializers

from payments_service.models import Payment
from users_service.serializer import UserSerializer


class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "borrowing",
            "session_id",
            "session_url",
            "status",
            "type",
            "created_at",
            "total_price",
        ]
        read_only_fields = ["id", "created_at"]


class PaymentListSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "session_url",
            "status",
            "type",
            "created_at",
            "total_price",
        ]
        read_only_fields = ["id", "created_at"]


class PaymentSerializerInBorrowing(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "type", "status"]
