from django.db import models

from borrowings_service.models import Borrowing
from users_service.models import User


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"
        EXPIRED = "EXPIRED"

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"

    borrowing = models.ForeignKey(
        Borrowing, on_delete=models.CASCADE, related_name="payments"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    session_id = models.CharField(max_length=400)
    session_url = models.URLField()
    status = models.CharField(
        max_length=100, choices=Status.choices, default=Status.PENDING
    )
    type = models.CharField(
        max_length=100,
        choices=Type.choices,
        default=Type.PAYMENT
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    total_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:
        return self.borrowing.book.title
