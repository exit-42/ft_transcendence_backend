import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

from log.models import Game, Match

import logging

logger = logging.getLogger('django')

def create_game(game_type):
    """
    @brief game을 생성하는 함수 (테스트 용도로만 사용할 임시 함수)

    @param game_type

    @return
        - 게임 생성 성공 : gameId
        - 에러 발생 : None

    @details
    게임을 시작할 때 호출하는 내부 API
    """
    try:
        is_tournament = False
        if game_type == "tournament":
            is_tournament = True

        game = Game.objects.create(isTournament=is_tournament)

        return game.gameId

    except Exception as e:
        return None


def set_game_end(game_id):
    """
    @brief game의 진행상태를 종료로 변경하는 함수 (테스트 용도로만 사용할 임시 함수)

    @param game_id

    @return
        - return 없음
    @details
    게임이 종료될 때 호출하는 내부 API
    """
    try:
        try:
            game = Game.objects.get(gameId=game_id)
        except Game.DoesNotExist:
            logger.info("log(set_game_end) : game does not exist : " + game_id)
            return

        game.isEnd = True
        game.save()

        return

    except Exception as e:
        return


def create_match_log(result):
    """
    @brief 게임 후 match 결과를 등록하는 함수 (테스트 용도로만 사용할 임시 함수)

    @param player_A_id, player_B_id, score_A, score_B, game_id, rank가 담긴 dictionary

    @return
        - 없음

    @details
    매치(1대1)가 종료될 때 호출하는 내부 API
    """
    logger.info("create match log start")
    try:

        required_fields = [
            "player_A_id",
            "player_B_id",
            "score_A",
            "score_B",
            "game_id",
            "rank",
        ]
        for key, value in result.items():
            logger.info(str(key) + " : " + str(value))
        if not all(field in result for field in required_fields):
            logger.info("log(create_match_log) : wrong argunemt")
            return

        player_A_id = result["player_A_id"]
        player_B_id = result["player_B_id"]
        score_A = result["score_A"]
        score_B = result["score_B"]
        game_id = result["game_id"]
        rank = result["rank"]

        try:
            player_A = User.objects.get(id=player_A_id)
            player_B = User.objects.get(id=player_B_id)
        except User.DoesNotExist:
            logger.info("log(create_match_log) : user does not exist")
            return

        try:
            game = Game.objects.get(gameId=game_id)
        except Game.DoesNotExist:
            logger.info("log(create_match_log) : game does not exist")
            return

        if game.isEnd == True:
            return

        Match.objects.create(
            playerA=player_A,
            playerB=player_B,
            scoreA=score_A,
            scoreB=score_B,
            game=game,
            rank=rank,
        )
        logger.info("log(create_match_log) : match created")
        return

    except Exception as e:
        logger.info("log(create_match_log) : fatal error!")
        logger.info("log(create_match_log) : " + str(e))
        return
