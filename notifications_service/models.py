from django.contrib.auth import get_user_model
from django.db import models


class Chat(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="chats",
    )
    chat_id = models.IntegerField(null=True)

    def __str__(self) -> str:
        return self.user.first_name
