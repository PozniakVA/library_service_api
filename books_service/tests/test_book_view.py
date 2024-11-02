from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


class BookViewTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_user(self) -> None:
        client = APIClient()

        response = client.get(
            reverse("books_service:book-list"),
        )
        response_2 = client.post(
            reverse("books_service:book-list"),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_read_only(self) -> None:

        response = self.client.post(
            reverse("books_service:book-list"),
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user(self) -> None:

        client = APIClient()
        admin_user = get_user_model().objects.create_user(
            email="admin@gmail.com",
            password="<PASSWORD>",
            is_staff=True,
        )
        client.force_authenticate(user=admin_user)

        data = {
            "title": "test",
            "daily_fee": 5
        }

        response = client.post(
            reverse("books_service:book-list"),
            data=data,

        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
