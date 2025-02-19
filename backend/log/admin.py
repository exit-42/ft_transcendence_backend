from django.contrib import admin

# Register your models here.

from .models import Game, Match


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """
    @brief GameAdmin 모델을 Django Admin에 등록하기 위한 설정
    @details GameAdmin 기능을 사용하여 게임 기록을 관리

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    @ordering 최근에 생성된 게임부터 표시
    """

    list_display = ("gameId", "isTournament", "isEnd", "createdAt")
    search_fields = ("gameId",)
    ordering = ("-createdAt",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """
    @brief MatchAdmin 모델을 Django Admin에 등록하기 위한 설정
    @details MatchAdmin 기능을 사용하여 개별 매치 기록을 관리

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    @ordering 최근에 생성된 매치부터 표시
    """

    list_display = (
        "matchId",
        "playerA",
        "playerB",
        "scoreA",
        "scoreB",
        "gameId",
        "rank",
        "createdAt",
    )
    search_fields = ("playerA__nickname", "playerB__nickname", "gameId")
    ordering = ("-createdAt",)
