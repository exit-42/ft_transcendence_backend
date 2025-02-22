import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from core.utils import authenticate_token

# Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()

from log.models import Game, Match


class logView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Game type (tournament or match)",
                ),
            },
            required=["type"],
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "gameId": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Type not provided"
                    )
                },
            ),
            401: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="Invalid or expired refresh token",
                    )
                },
            ),
            452: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Token refreshed"
                    )
                },
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Unexpected server error"
                    )
                },
            ),
        },
    )
    def post(self, request):
        """
        @brief game을 생성하는 함수 (테스트 용도로만 사용할 임시 함수)

        @param request Django의 HTTP 요청 객체

        @return
            - 게임 생성 성공 : gameId(pk)를 JSON으로 반환 (201)
            - 에러 발생 : 에러메시지 (4xx or 500)

        @details
        게임을 시작할 때 호출하는 내부 API
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            body = json.loads(request.body)
            game_type = body.get("type")

            if not game_type:
                return JsonResponse({"message": "Type not provided"}, status=400)

            is_tournament = False
            if game_type == "tournament":
                is_tournament = True

            game = Game.objects.create(isTournament=is_tournament)

            return JsonResponse({"gameId": game.gameId}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON format"}, status=400)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Game ID"),
            },
            required=["id"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="Game status changed successfully!",
                    ),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Game ID not provided"
                    )
                },
            ),
            401: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="Invalid or expired refresh token",
                    )
                },
            ),
            404: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Game not found"
                    )
                },
            ),
            409: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Game is already ended"
                    )
                },
            ),
            452: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Token refreshed"
                    )
                },
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Unexpected server error"
                    )
                },
            ),
        },
    )
    def patch(self, request):
        """
        @brief game의 진행상태를 종료로 변경하는 함수 (테스트 용도로만 사용할 임시 함수)

        @param request Django의 HTTP 요청 객체

        @return
            - isEnd 변경 성공 : 변경 성공 메시지 (200)
            - 게임 ID 제공되지 않음 : 에러 메시지 (400)
            - 게임이 존재하지 않음 : 에러 메시지 (404)
            - 게임이 이미 종료됨 : 에러 메시지 (409)
            - 인증 실패 : 에러 메시지 (401)
            - 기타 예외 발생 : 에러 메시지 (500)

        @details
        게임이 종료될 때 호출하는 내부 API
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            body = json.loads(request.body)
            game_id = body.get("id")

            if not game_id:
                return JsonResponse({"message": "Game id not provided"}, status=400)

            try:
                game = Game.objects.get(gameId=game_id)
            except Game.DoesNotExist:
                return JsonResponse({"message": "Game not found"}, status=404)

            if game.isEnd:
                return JsonResponse({"message": "Game is already ended"}, status=409)

            game.isEnd = True
            game.save()

            return JsonResponse(
                {"message": "Game status changed successfully!"}, status=200
            )

        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON format"}, status=400)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "player_A_id": openapi.Schema(
                type=openapi.TYPE_INTEGER, description="Player A ID"
            ),
            "player_B_id": openapi.Schema(
                type=openapi.TYPE_INTEGER, description="Player B ID"
            ),
            "score_A": openapi.Schema(
                type=openapi.TYPE_INTEGER, description="Player A Score"
            ),
            "score_B": openapi.Schema(
                type=openapi.TYPE_INTEGER, description="Player B Score"
            ),
            "game_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Game ID"),
            "rank": openapi.Schema(type=openapi.TYPE_INTEGER, description="Match Rank"),
        },
        required=[
            "player_A_id",
            "player_B_id",
            "score_A",
            "score_B",
            "game_id",
            "rank",
        ],
    ),
    responses={
        201: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Match created successfully!"
                ),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Invalid request data"
                )
            },
        ),
        401: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Invalid or expired refresh token"
                )
            },
        ),
        404: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="User or Game not found"
                )
            },
        ),
        500: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Unexpected server error"
                )
            },
        ),
    },
    operation_description="Creates a match record after a 1v1 game ends.",
    operation_summary="Create Match Log",
)
@api_view(["POST"])
def create_match_log(request):
    """
    @brief 게임 후 match 결과를 등록하는 함수 (테스트 용도로만 사용할 임시 함수)

        @param request Django의 HTTP 요청 객체

        @return
            - 매치 등록 성공 : "Match created successfully!" (201)
            - 유효하지 않은 요청 데이터 : "Invalid request data" (400)
            - 사용자가 존재하지 않음 : "User not found" (404)
            - 게임이 존재하지 않음 : "Game not found" (404)
            - 기타 서버 오류 발생 : 에러 메시지 (500)

        @details
        매치(1대1)가 종료될 때 호출하는 내부 API
    """
    try:
        user, token_response = authenticate_token(request)
        if token_response:
            return token_response

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON format"}, status=400)

        required_fields = [
            "player_A_id",
            "player_B_id",
            "score_A",
            "score_B",
            "game_id",
            "rank",
        ]
        if not all(field in body for field in required_fields):
            return JsonResponse({"message": "Invalid request data"}, status=400)

        player_A_id = body.get("player_A_id")
        player_B_id = body.get("player_B_id")
        score_A = body.get("score_A")
        score_B = body.get("score_B")
        game_id = body.get("game_id")
        rank = body.get("rank")

        try:
            player_A = User.objects.get(id=player_A_id)
            player_B = User.objects.get(id=player_B_id)
        except User.DoesNotExist:
            return JsonResponse({"message": "User not found"}, status=404)

        try:
            game = Game.objects.get(gameId=game_id)
        except Game.DoesNotExist:
            return JsonResponse({"message": "Game not found"}, status=404)

        if game.isEnd == True:
            return JsonResponse({"message": "Game not online"}, status=400)

        Match.objects.create(
            playerA=player_A,
            playerB=player_B,
            scoreA=score_A,
            scoreB=score_B,
            game=game,
            rank=rank,
        )
        return JsonResponse({"message": "match created successfully!"}, status=201)

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "game_type",
            openapi.IN_QUERY,
            description="Type of game to fetch (tournament or normal).",
            type=openapi.TYPE_STRING,
            required=True,
            enum=["tournament", "normal"],
        ),
        openapi.Parameter(
            "cursor",
            openapi.IN_QUERY,
            description="The gameId to start fetching results from (for pagination). Default is -1 (latest).",
            type=openapi.TYPE_INTEGER,
            required=False,
            default=-1,
        ),
    ],
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Games loaded successfully!"
                ),
                "games": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "gameId": openapi.Schema(
                                type=openapi.TYPE_INTEGER, example=102
                            ),
                            "isTournament": openapi.Schema(
                                type=openapi.TYPE_BOOLEAN, example=True
                            ),
                            "createdAt": openapi.Schema(
                                type=openapi.TYPE_STRING,
                                example="2025-02-21 15:45:30",
                            ),
                        },
                    ),
                ),
                "next_cursor": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    example=97,
                    description="Cursor for the next page. If null, no more data is available.",
                ),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Invalid cursor value or game type",
                )
            },
        ),
        401: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Invalid or expired refresh token",
                )
            },
        ),
        500: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Unexpected server error"
                )
            },
        ),
    },
    operation_description="Retrieve paginated list of completed games based on type (normal or tournament), ordered by most recent.",
    operation_summary="Get Game Logs",
)
@api_view(["GET"])
def get_game_logs(request):
    """
    @brief 특정 타입의 게임 로그를 가져오는 API

    @param request Django의 HTTP 요청 객체
        - game_type: "tournament" 또는 "normal" (필수)
        - cursor: gameId 기준으로 페이징 (기본값: -1)

    @return
        - 게임 조회 성공 : "Games loaded successfully!" (200)
        - 유효하지 않은 요청 데이터 : "Invalid cursor value or game type" (400)
        - 기타 서버 오류 발생 : 에러 메시지 (500)

    @details
        - Cursor-based Pagination 지원
    """
    try:
        user, token_response = authenticate_token(request)
        if token_response:
            return token_response

        game_type = request.GET.get("game_type")
        if game_type not in ["tournament", "normal"]:
            return JsonResponse({"message": "Invalid game type"}, status=400)

        cursor = request.GET.get("cursor", "-1")
        try:
            cursor = int(cursor)
        except ValueError:
            return JsonResponse({"message": "Invalid cursor value"}, status=400)

        if cursor < -1:
            return JsonResponse({"message": "Invalid cursor"}, status=400)

        is_tournament = True if game_type == "tournament" else False

        query = Game.objects.filter(isEnd=True, isTournament=is_tournament).order_by(
            "-gameId"
        )

        if cursor != -1:
            query = query.filter(gameId__lt=cursor)

        games = list(query[:5])

        next_cursor = games[-1].gameId if games else None

        game_list = []
        for game in games:
            matches = game.matches.all()
            match_list = [
                {
                    "playerA": match.playerA.nickname,
                    "playerB": match.playerB.nickname,
                    "playerAimagePath": match.playerA.imagePath,
                    "playerBimagePath": match.playerB.imagePath,
                    "scoreA": match.scoreA,
                    "scoreB": match.scoreB,
                    "rank": match.rank,
                }
                for match in matches
            ]

            game_list.append(
                {
                    "gameId": game.gameId,
                    "createdAt": game.createdAt.strftime("%Y-%m-%d %H:%M:%S"),
                    "matches": match_list,
                }
            )

        return JsonResponse(
            {
                "message": "Games loaded successfully!",
                "games": game_list,
                "next_cursor": next_cursor,
            },
            status=200,
        )

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
