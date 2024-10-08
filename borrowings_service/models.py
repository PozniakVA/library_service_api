from django.contrib.auth import get_user_model
from django.db import models

from books_service.models import Book


class Borrowings(models.Model):
    borrow_date = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(
        null=True,
        editable=False
    )
    book = models.ForeignKey(
        Book,
        related_name="borrowings",
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        get_user_model(),
        related_name="borrowings",
        on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return f"{self.borrow_date} - {self.expected_return_date}"
