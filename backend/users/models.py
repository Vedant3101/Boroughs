from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model — placeholder for future profile fields."""

    email = models.EmailField(unique=True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self) -> str:
        return self.username
