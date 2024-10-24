import stripe
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from borrowings_service.models import Borrowings
from library_service_api import settings
from notifications_service.bot_init import bot
from notifications_service.models import Chat
from payments_service.models import Payments


@shared_task
def reminder_to_return_the_book_in_one_day(user, book_title):
    chat = Chat.objects.get(user=user)
    bot.send_message(
        chat.chat_id,
        f"Dear {chat.user.first_name}, this is a reminder"
        f" that you planned to return the {book_title} in 24 hours",
    )


@shared_task
def reminder_to_return_the_book(user, book_title):
    chat = Chat.objects.get(user=user)
    bot.send_message(
        chat.chat_id,
        f"Dear {chat.user.first_name}, this is a reminder"
        f" that you planned to return the {book_title} today",
    )


@shared_task
def send_borrowing_success(user, book_title):
    chat = Chat.objects.get(user=user)
    bot.send_message(
        chat.chat_id,
        f"The book 📚{book_title}📚 has been borrowed successfully!"
    )


@shared_task
def send_return_borrowing_success(user, book_title):
    chat = Chat.objects.get(user=user)
    bot.send_message(
        chat.chat_id,
        f"The book 📚{book_title}📚 has been returned successfully!"
    )


@shared_task
def connect_telegram_user_with_user_from_db(message):
    text = message.text.split()
    if len(text) > 1:
        token = message.text.split()[1]
        user = get_user_model().objects.get(token=token)
        Chat.objects.create(user=user, chat_id=message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            """
If you have issues receiving messages, please re-enter the bot
using the link in your personal profile on the website.
""",
        )


@shared_task
def send_welcome_message(message):
    bot.send_message(
        message.chat.id,
        """
Hi! I’m LibraTrackBot — your assistant for the online library.

Here’s how I can help:
🔔 Get notified when you borrow or return a book.
📅 I’ll remind you when it’s time to return a book.
⏰ Get alerts if your rental period has passed.
""",
    )


@shared_task
def check_overdue_borrowing():
    overdue_borrowings = Borrowings.objects.filter(
        expected_return_date__lt=timezone.now(),
        actual_return_date__isnull=True
    )
    return overdue_borrowings


@shared_task
def send_notification_about_overdue_to_users():
    overdue_borrowings = check_overdue_borrowing()
    if overdue_borrowings:
        for borrowing in overdue_borrowings:
            chat = Chat.objects.get(user=borrowing.user)
            bot.send_message(
                chat.chat_id,
                f"Dear {chat.user.first_name}, the borrowing of your book "
                f"'{borrowing.book.title}' is overdue"
                f" as of {borrowing.expected_return_date}."
                f" Please don't forget to return the book."
            )


@shared_task
def send_notification_about_overdue_to_admin():
    overdue_borrowings = check_overdue_borrowing()

    if overdue_borrowings:
        message = ""
        for borrowing in overdue_borrowings:
            text = (
                f"{borrowing.user.email} overdue the book "
                f"{borrowing.book.title} "
                f"(The expected return date was "
                f"{borrowing.expected_return_date})\n"
            )
            message += text

        message = message[:-1]

    else:
        message = "No borrowings overdue today!"

    admin_chats = Chat.objects.filter(user__is_staff=True)
    for admin_chat in admin_chats:
        bot.send_message(
            admin_chat.chat_id,
            message
        )


@shared_task
def send_notification_about_successful_payment(chat_id):
    chat = Chat.objects.get(user=chat_id)
    bot.send_message(
        chat.chat_id,
        "The payment was successful"
    )


@shared_task
def send_notification_about_expired_payment(chat_id):
    chat = Chat.objects.get(user=chat_id)
    bot.send_message(
        chat.chat_id,
        "The payment expired"
    )


@shared_task
def checking_stripe_session_for_expiration():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    expires = stripe.checkout.Session.list(status="expired")

    for expire in expires:
        try:
            payment = Payments.objects.get(session_id=expire.id)
            payment.status = "EXPIRED"
            payment.save()
        except Payments.DoesNotExist:
            pass
