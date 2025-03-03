import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from core.utils import authenticate_token
from .roommanager import *

User = get_user_model()


# Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class roomView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "mode",
                openapi.IN_QUERY,
                description="game mode(individual or tournament)",
                type=openapi.TYPE_STRING,
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "games": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "roomId": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, example=102
                                ),
                                "playerCount": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, example=1
                                ),
                                "roomManager": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="userName",
                                ),
                            },
                        ),
                    ),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="invalid query argument"
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
    def get(self, request):
        """
        @brief 게임 방 목록 조회 (특정 모드의 방만 필터링 가능)

        @param request Django의 HTTP 요청 객체

        @return
            - 성공 시: 방 목록과 200 상태 코드
            - 실패 시: 오류 메시지와 400 또는 500 상태 코드
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            mode = request.GET.get("mode")  # URL 파라미터로 mode 필터링

            if not mode:
                return JsonResponse({"message": "invalid query argument"}, status=400)
            rooms = [
                {
                    "roomId": room_id,
                    "playerCount": room_data["player_number"],
                    "roomManager": room_data["room_manager"],
                    "start": room_data["start"],
                }
                for room_id, room_data in room_manager.rooms.items()
                if mode is None
                or room_data.get("mode") == mode
                and room_data["player_number"] > 0
            ]

            return JsonResponse({"data": rooms}, status=200)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "mode": openapi.Schema(
                    type=openapi.TYPE_STRING, description="game mode"
                ),
            },
            required=["name"],
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "room_id": openapi.Schema(type=openapi.TYPE_STRING, example="1"),
                    "port": openapi.Schema(type=openapi.TYPE_STRING, example="10001"),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="need mode argument"
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
        @brief 새로운 게임 방 생성

        @param request Django의 HTTP 요청 객체

        @return
            - 성공 시: 생성된 방 ID와 포트 정보, 201 상태 코드
            - 실패 시: 오류 메시지와 400 또는 500 상태 코드
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            data = json.loads(request.body)
            mode = data.get("mode")

            if not mode:
                return JsonResponse({"message": "need mode argument"}, status=400)

            room_id, port = room_manager.create_room(mode)
            if room_id is None:
                return JsonResponse({"message": "interal server error"}, status=500)
            if room_id:
                room_manager.join_room(room_id, user)

            return JsonResponse({"room_id": room_id, "port": port}, status=201)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "room_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="room_id"
                ),
            },
            required=["room_id"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "roomId": openapi.Schema(type=openapi.TYPE_STRING, example="1"),
                    "port": openapi.Schema(type=openapi.TYPE_STRING, example="10001"),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="need room_id"
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
                        type=openapi.TYPE_STRING, example="cannot join room"
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
        @brief 기존 게임 방 입장

        @param request Django의 HTTP 요청 객체

        @return
            - 성공 시: 입장한 방의 ID와 포트 정보, 200 상태 코드
            - 실패 시: 오류 메시지와 400 또는 500 상태 코드
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            data = json.loads(request.body)
            room_id = data.get("room_id")

            if room_id is None:
                return JsonResponse({"message": "need room_id"}, status=400)

            room_data = room_manager.join_room(room_id, user)
            if not room_data:
                return JsonResponse({"message": "cannot join room"}, status=404)

            return JsonResponse(
                {"roomId": room_id, "port": room_data["socket_port_number"]}, status=200
            )

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)
