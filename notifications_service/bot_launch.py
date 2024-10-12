from notifications_service.bot_init import bot
from notifications_service.tasks import (
    connect_telegram_user_with_user_from_db,
    send_welcome_message,
)


@bot.message_handler(commands=["start"])
def bot_launch(message):
    connect_telegram_user_with_user_from_db(message)
    send_welcome_message(message)


bot.infinity_polling()
