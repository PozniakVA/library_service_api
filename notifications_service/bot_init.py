import os

import django
import telebot
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_service_api.settings")
django.setup()
