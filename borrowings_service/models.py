from django.db import models
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from books_service.models import Book
from users_service.models import User


class Borrowing(models.Model):
    borrow_date = models.DateTimeField(auto_now_add=True, editable=False)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, editable=False)
    book = models.ForeignKey(
        Book,
        related_name="borrowings",
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        related_name="borrowings",
        on_delete=models.CASCADE
    )

    def clean(self):
        if not self.borrow_date:
            self.borrow_date = timezone.now()

        if self.expected_return_date < self.borrow_date:
            raise ValidationError("Expected return date cannot be in the past")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.user.email}"
            f" - {self.book.title}"
            f" - {self.expected_return_date}"
        )
