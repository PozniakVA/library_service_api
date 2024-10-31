import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from borrowings_service.models import Borrowing
from notifications_service.models import Chat
from notifications_service.tasks import (
    send_notification_about_successful_payment,
    send_notification_about_expired_payment,
)
from payments_service.models import Payment
from payments_service.permissions import (
    IsAdminUserOrIsAuthenticatedReadOnly
)
from payments_service.serializer import (
    PaymentSerializer,
    PaymentListSerializer,
)
from users_service.models import User


class PaymentViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAdminUserOrIsAuthenticatedReadOnly]
    queryset = Payment.objects.select_related()

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
    if total_price < 1:
        total_price = 1

    return float(total_price)


def calculate_fine(borrowing):
    FINE_MULTIPLIER = 1.6
    SECONDS_IN_ONE_DAY = 86400

    overdue_time_in_seconds = (
            borrowing.actual_return_date - borrowing.expected_return_date
    ).total_seconds()
    overdue_days = overdue_time_in_seconds / SECONDS_IN_ONE_DAY

    overdue_days = Decimal(overdue_days)
    daily_fee = Decimal(borrowing.book.daily_fee)
    FINE_MULTIPLIER = Decimal(FINE_MULTIPLIER)

    total_fine = round((daily_fee * overdue_days * FINE_MULTIPLIER), 2)
    if total_fine < 1:
        total_fine = 1

    return float(total_fine)


def create_checkout_session(
        request,
        borrowing,
        total_price,
        type_payment
):
    stripe.api_key = settings.STRIPE_SECRET_KEY

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
            "type_payment": type_payment,
            "email": borrowing.user.email,
            "first_name": borrowing.user.first_name,
            "last_name": borrowing.user.last_name,
            "book_title": borrowing.book.title,
        },
    )
    Payment.objects.create(
        user=request.user,
        borrowing=borrowing,
        session_id=checkout_session.id,
        session_url=checkout_session.url,
        status="PENDING",
        type=type_payment,
        total_price=total_price,
    )
    return redirect(checkout_session.url, code=303)


def pay_payment(request, borrowing_id):
    borrowing = Borrowing.objects.get(id=borrowing_id)
    type_payment = "PAYMENT"
    total_price = calculate_total_price(borrowing)
    return create_checkout_session(
        request,
        borrowing,
        total_price,
        type_payment
    )


@extend_schema(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Borrowing not found."},
        status.HTTP_400_BAD_REQUEST: {
            "description":
                "Your session is still active, you do not"
                " need to renew it OR Your borrowing does not need payment",
        },
        status.HTTP_302_FOUND: {
            "description": "Redirects to the payment page(Stripe)."
        },
    },
    description="Resumes the payment checkout"
                " session so that the user can pay",
)
@api_view()
def renew_payment(request, borrowing_id):

    try:
        borrowing = Borrowing.objects.get(id=borrowing_id)
    except Borrowing.DoesNotExist:
        return Response(
            {"detail": "Borrowing not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if borrowing.payments.filter(type="PAYMENT", status="PENDING"):
        return Response(
            {
                "detail":
                    "Your session is still active, you do not need to renew it"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if borrowing.payments.filter(type="PAYMENT", status="PAID"):
        return Response(
            {"detail": "Your borrowing does not need payment"},
            status=status.HTTP_400_BAD_REQUEST
        )

    type_payment = "PAYMENT"
    total_price = calculate_total_price(borrowing)
    return create_checkout_session(
        request,
        borrowing,
        total_price,
        type_payment
    )


@extend_schema(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Borrowing not found."},
        status.HTTP_400_BAD_REQUEST: {
            "description":
                "Your borrowing does not need payment of a fine",
        },
        status.HTTP_302_FOUND: {
            "description": "Redirects to the payment page(Stripe)."
        },
    },
    description="Create a new checkout session to pay the fine",
)
@api_view()
def fine_payment(request, borrowing_id):

    try:
        borrowing = Borrowing.objects.get(id=borrowing_id)
    except Borrowing.DoesNotExist:
        return Response(
            {"detail": "Borrowing not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if (not borrowing.actual_return_date or
            borrowing.actual_return_date <= borrowing.expected_return_date):
        return Response(
            {"detail": "Your borrowing does not need payment of a fine"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if borrowing.payments.filter(type="FINE", status="PAID"):
        return Response(
            {"detail": "Your borrowing does not need payment of a fine"},
            status=status.HTTP_400_BAD_REQUEST
        )

    type_payment = "FINE"
    total_price = calculate_fine(borrowing)
    return create_checkout_session(
        request,
        borrowing,
        total_price,
        type_payment
    )


@extend_schema(
    description="The endpoint is created to listen for "
                "responses from Stripe after payment, the"
                " user does not need to communicate with it",
)
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
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
        type_payment = session.metadata.get("type_payment")

        borrowing = Borrowing.objects.get(id=borrowing_id)
        payment = Payment.objects.get(
            borrowing__id=borrowing_id,
            type=type_payment
        )

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
        email = session.metadata.get("email")
        user = User.objects.get(email=email)

        try:
            chat = Chat.objects.get(user=user)
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
