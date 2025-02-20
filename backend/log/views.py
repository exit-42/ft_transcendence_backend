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
        @brief game을 생성하는 함수 (Django 서버 내부에서 사용하는 API)

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
        @brief game의 진행상태를 종료로 변경하는 함수 (Django 서버 내부에서 사용하는 API)

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
