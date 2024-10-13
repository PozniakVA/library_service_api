from django.db import models

from users_service.models import User


class Chat(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chats",
    )
    chat_id = models.IntegerField(null=True)

    def __str__(self) -> str:
        return self.user.first_name
