from django.core.management.base import BaseCommand

from notifications_service.bot_init import bot
from notifications_service.tasks import (
    connect_telegram_user_with_user_from_db,
    send_welcome_message
)


class Command(BaseCommand):
    """Launching a telegram bot."""

    def handle(self, *args, **options):
        self.stdout.write("Bot is running! Press Ctrl + C to stop the bot.")

        @bot.message_handler(commands=["start"])
        def bot_launch(message):
            connect_telegram_user_with_user_from_db(message)
            send_welcome_message(message)

        bot.infinity_polling()

        self.stdout.write(self.style.SUCCESS("Telegram bot is stopped"))
