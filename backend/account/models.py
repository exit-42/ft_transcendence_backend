from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    imagePath = models.URLField(max_length=255, blank=True, null=True)
    nickname = models.CharField(max_length=50, unique=True, blank=True, null=True)
    winCnt = models.PositiveIntegerField(default=0)
    loseCnt = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username


class OAuth(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="oauth_account"
    )
    intraId = models.CharField(max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.intraId
