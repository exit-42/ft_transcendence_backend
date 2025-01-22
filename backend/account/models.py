from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

# Create your models here.


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


class OAuth(models.Model):
    """
    @brief OAuth 모델 설정
    @details OAuth 기능을 사용하는 사용자의 인증정보를 관리

    @user OAuth 인증을 통해 특정되는 사용자
    @intraId 42서버로부터 OAuth 인증을 통해 수신할 수 있는 유저의 고유정보(인트라 아이디).
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="oauth_account"
    )
    intraId = models.CharField(max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.intraId


class LocalAuth(models.Model):
    """
    @brief LocalAuth 모델 설정
    @details LocalAuth 기능을 사용하는 사용자의 인증정보를 관리

    @user LocalAuth 인증을 통해 특정되는 사용자
    @localId LocalAuth 로그인에 사용되는 유저의 아이디.
    @localPassword LocalAuth 로그인에 사용되는 유저의 비밀번호.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="local_auth"
    )
    localId = models.CharField(max_length=30, unique=True, db_index=True)
    localPassword = models.CharField(max_length=30)

    def __str__(self):
        return self.localId
