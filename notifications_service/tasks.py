from celery import shared_task
from django.contrib.auth import get_user_model

from notifications_service.bot_init import bot
from notifications_service.models import Chat


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
