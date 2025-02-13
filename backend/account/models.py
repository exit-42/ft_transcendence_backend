from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    """
    @brief User 모델 설정
    @details 사용자의 프로필 정보를 관리

    @username 유저를 식별하는 고유한 문자열
    @imagePath 프로필 이미지 url path
    @nickname 유저가 스스로를 정의하는 별명
    @winCnt 유저의 1대1 매치 승리 횟수
    @loseCnt 유저의 1대1 매치 패배 횟수
    """

    username = models.CharField(
        max_length=36, unique=True, default=uuid.uuid4, editable=False
    )
    imagePath = models.URLField(max_length=255, null=True)
    nickname = models.CharField(max_length=50, unique=True)
    winCnt = models.PositiveIntegerField(default=0)
    loseCnt = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username
