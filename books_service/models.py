from django.core.validators import MinValueValidator
from django.db import models


class Book(models.Model):

    class Cover(models.TextChoices):
        HARD = "hard cover"
        SOFT = "soft cover"

    title = models.CharField(max_length=100)
    author = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    cover = models.CharField(
        max_length=100,
        choices=Cover.choices,
        null=True,
        blank=True
    )
    inventory = models.IntegerField(
        validators=[MinValueValidator(1)],
        null=True,
        blank=True
    )
    daily_fee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
    )

    def __str__(self) -> str:
        return self.title
