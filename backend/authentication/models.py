from django.db import models
from account.models import User


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
    intraId = models.CharField(max_length=255, primary_key=True)

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
    localId = models.CharField(max_length=255, primary_key=True)
    localPassword = models.CharField(max_length=200)

    def __str__(self):
        return self.localId
