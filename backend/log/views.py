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
        지정한 타입의 게임을 생성한다.
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
