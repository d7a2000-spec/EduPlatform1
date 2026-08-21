from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("platform_admin", "مدير المنصة"),
        ("school_admin", "مدير المدرسة"),
        ("teacher", "مدرس"),
        ("student", "طالب"),
        ("parent", "ولي أمر"),
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="student",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    def __str__(self):
        return self.username