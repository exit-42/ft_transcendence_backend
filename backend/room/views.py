import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from core.utils import authenticate_token
from .room_manager import *

User = get_user_model()


# Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# DRF Parsers
from rest_framework.parsers import MultiPartParser, FormParser  # Import parsers



class roomView(APIView):
    def get(self, request):
        """ 방 목록 조회 (특정 모드에 해당하는 방 필터링) """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            mode = request.GET.get("mode")  # URL 파라미터로 mode 필터링

            rooms = [
                {
                    "room_id": room_id,
                    "player_count": room_data["player_number"],
                    "room_manager": room_data["room_manager"]
                }
                for room_id, room_data in room_manager.rooms.items()
                if mode is None or room_data.get("mode") == mode  # mode 필터링 (없으면 모든 방)
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
                    "room_id": openapi.Schema(
                        type=openapi.TYPE_STRING, example="1"
                    ),
                    "port": openapi.Schema(
                        type=openapi.TYPE_STRING, example="10001"
                    ),
                },
            ),
        },
    )
    def post(self, request):
        """ 새로운 방 생성 (방장 이름과 게임 모드 필요) """

        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response
            
            data = json.loads(request.body)
            player_name = user.nickname
            mode = data.get("mode")

            if not mode:
                return JsonResponse({"message": "need mode argument"}, status=400)

            room_id, port = room_manager.create_room(mode)
            if room_id:
                room_manager.join_room(room_id, user)

            return JsonResponse({
                "room_id": room_id,
                "port": port
            }, status=201)


        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    def patch(self, request):
        """ 기존 방 입장 (room_id와 player_name 필요) """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response
            
            data = json.loads(request.body)
            room_id = data.get("room_id")
            player_name = user.nickname

            if room_id is None:
                return JsonResponse({"message": "need room_id"}, status=400)

            room_data = room_manager.join_room(room_id, player_name)
            if not room_data:
                return JsonResponse({"message": "cannot join room"}, status=404)

            return JsonResponse({
                "room_id": room_id,
                "port": room_data["socket_port_number"]
            }, status=200)


        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)
    