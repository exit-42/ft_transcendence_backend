from django.db import models
from account.models import User


class Follow(models.Model):
    """
    @brief Follow 모델 설정
    @details 유저의 Follow 관리

    @followId Follow 중간테이블의 Primary key
    @userA userB를 팔로우 하는 userA (외래키)
    @userB userA가 팔로우 하는 userB (외래키)
    @createdAt follow 관계가 생성된 시점
    """

    followId = models.AutoField(primary_key=True)
    userA = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    userB = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.userA.nickname} follows {self.userB.nickname}"
