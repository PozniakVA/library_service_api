from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from books_service.models import Book
from borrowings_service.models import Borrowing
from payments_service.views import calculate_total_price, calculate_fine


class CalculatePricesTest(TestCase):
    def setUp(self) -> None:
        book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=5
        )
        user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test12345",
        )
        self.borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            actual_return_date=timezone.now() + timedelta(days=5),
            book=book,
            user=user
        )

    def test_calculate_total_price(self) -> None:
        result = calculate_total_price(self.borrowing)
        self.assertEqual(result, 15.0)

    def test_calculate_fine(self) -> None:
        result = calculate_fine(self.borrowing)
        self.assertEqual(result, 16.0)
