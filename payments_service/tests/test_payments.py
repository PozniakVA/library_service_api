from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books_service.models import Book
from borrowings_service.models import Borrowing
from notifications_service.models import Chat
from payments_service.models import Payment


def detail_url(endpoint, object_id):
    return reverse(f"payments_service:{endpoint}", args=[object_id])


class WebhookTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.webhook_url = reverse("payments_service:stripe-webhook")

        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test12345",
        )
        self.client.force_authenticate(user=self.user)

        book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=5
        )

        self.borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=book,
            user=self.user,
        )

        self.chat = Chat.objects.create(
            user=self.user,
            chat_id=5
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            user=self.user,
            session_id="session_id",
            session_url="https://session_url",
            status="PENDING",
            type="PAYMENT",
            total_price=10,
        )

        self.payload = {
            "type": "",
            "data": {
                "object": {
                    "metadata": {
                        "borrowing_id": self.borrowing.id,
                        "type_payment": "PAYMENT",
                        "email": self.user.email,
                    }
                }
            }
        }

    @patch(
        "payments_service.views.send_notification_about_successful_payment.delay"
    )
    def test_checkout_session_completed_success(
            self,
            mock_send_notification
    ) -> None:

        self.payload["type"] = "checkout.session.completed"
        response = self.client.post(
            self.webhook_url,
            data=self.payload,
            format="json"
        )

        payment = Payment.objects.get(borrowing__id=self.borrowing.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment.status, "PAID")
        mock_send_notification.assert_called_once_with(self.chat.id)

    @patch(
        "payments_service.views.send_notification_about_expired_payment.delay"
    )
    def test_checkout_session_expired(self, mock_send_notification) -> None:

        self.payload["type"] = "checkout.session.expired"
        response = self.client.post(
            self.webhook_url,
            data=self.payload,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_notification.assert_called_once_with(self.chat.id)


class RenewPaymentsTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test12345",
        )
        self.client.force_authenticate(user=self.user)
        book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=5
        )
        self.borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=book,
            user=self.user,
        )

    def test_borrowing_does_not_exist(self) -> None:
        response = self.client.get(detail_url("renew_payment", 1000))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_is_still_active_does_not_need_renew(self) -> None:

        Payment.objects.create(
            borrowing=self.borrowing,
            user=self.user,
            session_id="session_id",
            session_url="https://session_url",
            status="PENDING",
            type="PAYMENT",
            total_price=10,
        )

        response = self.client.get(
            detail_url("renew_payment", self.borrowing.id)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_your_borrowing_does_not_need_payment(self) -> None:

        Payment.objects.create(
            borrowing=self.borrowing,
            user=self.user,
            session_id="session_id",
            session_url="https://session_url",
            status="PAID",
            type="PAYMENT",
            total_price=10,
        )

        response = self.client.get(
            detail_url("renew_payment", self.borrowing.id)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_moved_to_another_URL(self) -> None:
        response = self.client.get(
            detail_url("renew_payment",
                       self.borrowing.id)
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)


class FinePaymentsTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test12345",
        )
        self.client.force_authenticate(user=self.user)
        self.book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=5
        )

    def test_borrowing_does_not_exist(self) -> None:
        response = self.client.get(detail_url("fine_payment", 1000))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_does_not_need_payment_when_actual_return_date_less_expected_date(
            self
    ) -> None:

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            actual_return_date=timezone.now() + timedelta(days=2),
            book=self.book,
            user=self.user,
        )

        response = self.client.get(detail_url("fine_payment", borrowing.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_does_not_need_payment_when_there_is_no_actual_return_date(
            self
    ) -> None:

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=self.book,
            user=self.user,
        )

        response = self.client.get(detail_url("fine_payment", borrowing.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_your_borrowing_does_not_need_payment(self) -> None:

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            actual_return_date=timezone.now() + timedelta(days=5),
            book=self.book,
            user=self.user,
        )

        Payment.objects.create(
            borrowing=borrowing,
            user=self.user,
            session_id="session_id",
            session_url="https://session_url",
            status="PAID",
            type="FINE",
            total_price=10,
        )

        response = self.client.get(detail_url("fine_payment", borrowing.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_moved_to_another_URL(self) -> None:

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            actual_return_date=timezone.now() + timedelta(days=4),
            book=self.book,
            user=self.user,
        )

        response = self.client.get(detail_url("fine_payment", borrowing.id))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)


class PaymentViewSetTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="<PASSWORD>",
            is_staff=False,
        )

        book = Book.objects.create(
            title="Test Book",
            inventory=100,
            daily_fee=5
        )

        borrowing = Borrowing.objects.create(
            expected_return_date=timezone.now() + timedelta(days=3),
            book=book,
            user=self.user,
        )

        self.payment = Payment.objects.create(
            borrowing=borrowing,
            user=self.user,
            session_id="session_id",
            session_url="https://session_url",
            status="PENDING",
            type="PAYMENT",
            total_price=10,
        )

    def test_unauthenticated_user_method_get_forbidden(self) -> None:
        response = self.client.get(
            reverse("payments_service:payments-list")
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_method_patch_forbidden(self) -> None:
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            detail_url("payments-detail", self.payment.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_class_admin_method_patch_allowed(self) -> None:
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

        update_data = {
            "status": "EXPIRED",
        }

        response = self.client.patch(
            detail_url("payments-detail", self.payment.id),
            data=update_data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
