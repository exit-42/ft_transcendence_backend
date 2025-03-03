import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

from log.models import Game, Match

import logging

logger = logging.getLogger("django")


def create_game(game_type):
    """
    @brief game을 생성하는 함수

    @param game_type

    @return
        - 게임 생성 성공 : gameId
        - 에러 발생 : None

    @details 게임을 시작할 때 호출하는 내부 API
    """
    try:
        is_tournament = False
        if game_type == "tournament":
            is_tournament = True

        game = Game.objects.create(isTournament=is_tournament)

        return game.gameId

    except Exception as e:
        logger.debug("create_game :" + str(e))
        return None


def set_game_end(game_id):
    """
    @brief game의 진행상태를 종료로 변경하는 함수

    @param game_id

    @return
        - 성공 : True
        - 에러 발생 : False

    @details 게임이 종료될 때 호출하는 내부 API
    """
    try:
        try:
            game = Game.objects.get(gameId=game_id)
        except Game.DoesNotExist:
            logger.debug("set_game_end : game not exist " + str(game_id))
            return False

        game.isEnd = True
        game.save()

        return True

    except Exception as e:
        logger.debug("set_game_end :" + str(e))
        return False


def create_match_log(result):
    """
    @brief 게임 후 match 결과를 등록하는 함수

    @param player_A_id, player_B_id, score_A, score_B, game_id, rank가 담긴 dictionary

    @return
        - 성공 : True
        - 에러 발생 : False

    @details
    매치(1대1)가 종료될 때 호출하는 내부 API
    """
    try:

        required_fields = [
            "player_A_id",
            "player_B_id",
            "score_A",
            "score_B",
            "game_id",
            "rank",
        ]
        if not all(field in result for field in required_fields):
            logger.debug("create_match_log : wrong argument")
            return False

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
            logger.debug("create_match_log : user not exist")
            return False

        try:
            game = Game.objects.get(gameId=game_id)
        except Game.DoesNotExist:
            logger.debug("create_match_log : game not exist " + str(game_id))
            return False

        if game.isEnd == True:
            logger.debug("create_match_log : already game end")
            return False

        Match.objects.create(
            playerA=player_A,
            playerB=player_B,
            scoreA=score_A,
            scoreB=score_B,
            game=game,
            rank=rank,
        )
        return True

    except Exception as e:
        logger.debug("create_match_log : " + str(e))
        return False
