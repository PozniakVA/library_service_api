from datetime import timedelta
from unittest.mock import patch, ANY

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from books_service.models import Book
from borrowings_service.models import Borrowing
from borrowings_service.serializer import BorrowingListSerializer
from payments_service.models import Payment


class TestBorrowingCreate(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="<PASSWORD>",
        )
        self.client.force_authenticate(user=self.user)

        self.book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=10
        )

        self.data = {
            "book": self.book.id,
            "expected_return_date": timezone.now() + timedelta(days=3),
        }

    def test_pay_previous_borrowings_first(self) -> None:

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=self.book,
            user=self.user,
        )

        Payment.objects.create(
            borrowing=borrowing,
            user=self.user,
            session_id="session_id",
            session_url="https://session_url",
            status="PENDING",
            type="PAYMENT",
            total_price=10,
        )

        response = self.client.post(
            reverse("borrowings_service:borrowing-list")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_book_not_found(self) -> None:

        data = self.data
        data["book"] = 1000

        response = self.client.post(
            reverse("borrowings_service:borrowing-list"),
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_copies_of_book_are_not_available(self) -> None:
        self.book.inventory = 0
        self.book.save()

        data = {
            "book": self.book.id,
            "expected_return_date": timezone.now() + timedelta(days=3),
        }

        response = self.client.post(
            reverse("borrowings_service:borrowing-list"),
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("borrowings_service.views.reminder_to_return_the_book_in_one_day.apply_async")
    @patch("borrowings_service.views.reminder_to_return_the_book.apply_async")
    @patch("borrowings_service.views.send_borrowing_success.delay")
    @patch("borrowings_service.views.pay_payment")
    def test_create_borrowing(
            self,
            mock_pay_payment,
            mock_send_borrowing_success,
            mock_reminder_to_return_the_book_in_one_day,
            mock_reminder_to_return_the_book,
    ) -> None:
        mock_pay_payment.return_value = Response(status=status.HTTP_200_OK)
        inventory = self.book.inventory

        data = {
            "book": self.book.id,
            "expected_return_date": timezone.now() + timedelta(days=6),
        }

        self.client.post(
            reverse("borrowings_service:borrowing-list"),
            data=data
        )

        borrowing = Borrowing.objects.get(book=self.book)
        self.book.refresh_from_db()

        self.assertEqual(Borrowing.objects.count(), 1)
        self.assertEqual(self.book.inventory, inventory - 1)
        self.assertEqual(borrowing.book.id, data["book"])
        self.assertEqual(
            borrowing.expected_return_date,
            data["expected_return_date"]
        )

        mock_send_borrowing_success.assert_called_once()
        mock_reminder_to_return_the_book.assert_called_once()

        if borrowing.expected_return_date >= borrowing.borrow_date + timedelta(days=1):
            mock_reminder_to_return_the_book_in_one_day.assert_called_once()
        else:
            mock_reminder_to_return_the_book_in_one_day.assert_not_called()


class TestBorrowingReturn(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="<PASSWORD>",
        )
        self.client.force_authenticate(user=self.user)

        self.book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=10
        )

    def test_book_already_returned(self) -> None:
        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=self.book,
            user=self.user,
            actual_return_date=timezone.now() + timedelta(days=3),
        )
        inventory = self.book.inventory

        response = self.client.post(
            reverse("borrowings_service:borrowing-detail", args=[borrowing.id])
            + "return/",
        )

        self.book.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.book.inventory, inventory)

    @patch("borrowings_service.views.send_return_borrowing_success.delay")
    def test_borrowing_return(self, mock_reminder_to_return_the_book) -> None:

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=self.book,
            user=self.user,
        )
        inventory = self.book.inventory

        response = self.client.post(
            reverse(
                "borrowings_service:borrowing-detail",
                args=[borrowing.id]) + "return/",
        )

        self.book.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.book.inventory, inventory + 1)
        mock_reminder_to_return_the_book.assert_called_once()

    @patch("borrowings_service.views.send_return_borrowing_success.delay")
    @patch("borrowings_service.views.render")
    @patch("borrowings_service.models.Borrowing.clean", return_value=None)
    def test_return_fine_page(
            self,
            mock_method_clean,
            mock_render,
            mock_send_return_borrowing_success
    ) -> None:

        mock_render.return_value = Response(status=status.HTTP_200_OK)

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() - timedelta(days=2),
            book=self.book,
            user=self.user,
        )

        self.client.post(
            reverse("borrowings_service:borrowing-detail", args=[borrowing.id])
            + "return/",
        )

        mock_send_return_borrowing_success.assert_called_once()
        mock_render.assert_called_once_with(
            ANY,
            "payments_service/fine_page.html",
            context={"context": borrowing}
        )


class TestBorrowing(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="<PASSWORD>",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

        self.user_2 = get_user_model().objects.create_user(
            email="test2@gmail.com",
            password="<PASSWORD>",
        )

        self.book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=10
        )

        self.borrowing_1 = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=self.book,
            user=self.user,
            actual_return_date=timezone.now() + timedelta(days=3),
        )
        self.borrowing_2 = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=self.book,
            user=self.user_2,
        )

        self.serializer_1 = BorrowingListSerializer(self.borrowing_1)
        self.serializer_2 = BorrowingListSerializer(self.borrowing_2)

    def test_filter_borrowings_by_is_active(self) -> None:

        response = self.client.get(
            reverse("borrowings_service:borrowing-list"),
            {"is_active": "True"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.serializer_2.data, response.data)
        self.assertNotIn(self.serializer_1.data, response.data)

    def test_filter_borrowings_by_user_id(self) -> None:

        response = self.client.get(
            reverse("borrowings_service:borrowing-list"),
            {"user_id": self.user_2.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.serializer_2.data, response.data)
        self.assertNotIn(self.serializer_1.data, response.data)

    def test_unauthenticated(self) -> None:

        client = APIClient()

        response = client.get(
            reverse("borrowings_service:borrowing-list"),
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
