from django.db import models
from account.models import User


class Game(models.Model):
    """
    @brief Game 모델 설정
    @details 게임 기록 관리

    @gameId Game 테이블의 Primary key
    @isTournament 게임의 종류가 토너먼트인지 아닌지(1대1 게임)
    @isEnd 게임이 진행중인지 아닌지
    @createdAt 게임이 생성된 시점
    """

    gameId = models.AutoField(primary_key=True)
    isTournament = models.BooleanField(default=False)
    isEnd = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gameId}"


class Match(models.Model):
    """
    @brief Match 모델 설정
    @details 게임 내 개별 매치 기록

    @matchId Match 테이블의 Primary key
    @playerA userA (외래키)
    @playerB userB (외래키)
    @scoreA userA의 점수
    @scoreB userB의 점수
    @gameId 게임 ID (Game 클래스의 pk)
    @rank 게임의 단계 (1대1 게임: 1, 토너먼트 1차전: 1, 토너먼트 2차전: 2, 토너먼트 결승전: 3)
    @createdAt 매치가 생성된 시점
    """

    matchId = models.AutoField(primary_key=True)
    playerA = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="matches_as_playerA"
    )
    playerB = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="matches_as_playerB"
    )
    scoreA = models.IntegerField(default=0)
    scoreB = models.IntegerField(default=0)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="matches")
    rank = models.PositiveIntegerField(default=1)
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.matchId}"
