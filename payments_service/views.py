import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from borrowings_service.models import Borrowings
from notifications_service.models import Chat
from notifications_service.tasks import (
    send_notification_about_successful_payment,
    send_notification_about_expired_payment,
)
from payments_service.models import Payments
from payments_service.permissions import IsAdminUserOrIsAuthenticatedReadOnly
from payments_service.serializer import (
    PaymentSerializer,
    PaymentListSerializer,
)


class PaymentsViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAdminUserOrIsAuthenticatedReadOnly]
    queryset = Payments.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        return PaymentSerializer


def calculate_total_price(borrowing):
    SECONDS_IN_ONE_DAY = 86400
    borrowing_seconds = (
        borrowing.expected_return_date - borrowing.borrow_date
    ).total_seconds()
    borrowing_days = borrowing_seconds / SECONDS_IN_ONE_DAY

    borrowing_days = Decimal(borrowing_days)
    daily_fee = Decimal(borrowing.book.daily_fee)

    total_price = round((daily_fee * borrowing_days), 2)
    return float(total_price)


def stripe_payment(request, borrowing):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    total_price = calculate_total_price(borrowing)

    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": borrowing.book.title},
                    "unit_amount": int(total_price * 100),
                },
                "quantity": 1,
            },
        ],
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("payments_service:successful_page")
        )
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(
            reverse("payments_service:canceled_page")
        ),
        metadata={
            "borrowing_id": borrowing.id,
            "email": borrowing.user.email,
            "first_name": borrowing.user.first_name,
            "last_name": borrowing.user.last_name,
            "book_title": borrowing.book.title,
        },
    )
    Payments.objects.create(
        borrowing=borrowing,
        session_id=checkout_session.id,
        session_url=checkout_session.url,
        status="PENDING",
        type="PAYMENT",
        total_price=total_price,
    )
    return redirect(checkout_session.url, code=303)


@csrf_exempt
@api_view(("POST",))
def my_webhook_view(request):
    payload = request.body
    event = None

    try:
        event = stripe.Event.construct_from(
            json.loads(payload),
            stripe.api_key
        )
    except ValueError:
        return Response(
            {"detail": "Invalid payload"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session = event.data.object

    if event.type == "checkout.session.completed":
        borrowing_id = int(session.metadata.get("borrowing_id"))
        borrowing = Borrowings.objects.get(id=borrowing_id)

        payment = Payments.objects.get(borrowing__id=borrowing_id)
        payment.status = "PAID"
        payment.save()

        try:
            chat = Chat.objects.get(user=borrowing.user)
            send_notification_about_successful_payment.delay(chat.id)
        except Chat.DoesNotExist:
            pass

        return Response(
            {"detail": "Payment is successful!"},
            status=status.HTTP_200_OK
        )

    if event.type == "checkout.session.expired":
        borrowing_id = int(session.metadata.get("borrowing_id"))
        borrowing = Borrowings.objects.get(id=borrowing_id)

        try:
            chat = Chat.objects.get(user=borrowing.user)
            send_notification_about_expired_payment.delay(chat.id)
        except Chat.DoesNotExist:
            pass

        return Response(
            {"detail": "The payment expired!"},
            status=status.HTTP_200_OK
        )

    return Response(status=status.HTTP_200_OK)


def successful_page(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(request.GET.get("session_id"))
    customer = session.metadata
    return render(
        request,
        "payments_service/successful_page.html",
        context={"customer": customer}
    )


def canceled_page(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(request.GET.get("session_id"))
    customer = session.metadata
    return render(
        request,
        "payments_service/canceled_page.html",
        context={"customer": customer}
    )
