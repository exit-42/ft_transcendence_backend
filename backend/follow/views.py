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

from follow.models import Follow


class followView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "word",
                openapi.IN_QUERY,
                description="Search keyword",
                type=openapi.TYPE_STRING,
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "data": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "nickname": openapi.Schema(type=openapi.TYPE_STRING),
                                "imagePath": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                    ),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Word not provided"
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
                        type=openapi.TYPE_STRING, example="User not found"
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
        @brief nickname을 통해 유저를 검색하는 함수

        @param request Django의 HTTP 요청 객체

        @return
            - 유저 발견 O : 유저 데이터 반환, 유저 발견 성공 메시지(200)
            - 유저 발견 X : 유저 발견 실패 메시지(404)
            - 에러 발생 : 에러메시지(400 or 500)

        @details
        특정 문자열을 포함한 닉네임을 가진 유저들을 탐색한다.
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            word = request.GET.get("word")
            if not word:
                return JsonResponse({"message": "Word not provided"}, status=400)

            users = User.objects.filter(nickname__icontains=word)

            if not users.exists():
                return JsonResponse({"message": "User not found"}, status=404)

            user_list = [
                {
                    "nickname": searched_user.nickname,
                    "imagePath": searched_user.imagePath,
                }
                for searched_user in users
            ]

            return JsonResponse(
                {"message": "User found", "data": user_list}, status=200
            )

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="user nickname"
                ),
            },
            required=["name"],
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Follow complete"
                    ),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Nickname not provided"
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
            403: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="You cannot follow yourself"
                    )
                },
            ),
            404: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="User not found"
                    )
                },
            ),
            409: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Already exist"
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
    @csrf_exempt
    def post(self, request):
        """
        @brief 특정 유저를 팔로우하는 함수

        @param request Django의 HTTP 요청 객체

        @return
            - 팔로우 성공 : "Follow complete" (201)
            - 자기 자신을 팔로우할 경우 : "You cannot follow yourself" (403)
            - 이미 팔로우한 경우 : "Already exist" (409)
            - 유저가 존재하지 않는 경우 : "User not found" (404)
            - 기타 예외 발생 : 에러 메시지 (500)
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            body = json.loads(request.body)
            nickname = body.get("name")

            if not nickname:
                return JsonResponse({"message": "Nickname not provided"}, status=400)

            try:
                target_user = User.objects.get(nickname=nickname)
            except User.DoesNotExist:
                return JsonResponse({"message": "User not found"}, status=404)

            if user == target_user:
                return JsonResponse(
                    {"message": "You cannot follow yourself"}, status=403
                )

            if Follow.objects.filter(userA=user, userB=target_user).exists():
                return JsonResponse({"message": "Already exist"}, status=409)

            Follow.objects.create(userA=user, userB=target_user)
            return JsonResponse({"message": "Follow complete"}, status=201)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="user nickname"
                ),
            },
            required=["name"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Unfollow complete"
                    ),
                },
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, example="Nickname not provided"
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
                        type=openapi.TYPE_STRING, example="Follow relation not found"
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
    @csrf_exempt
    def delete(self, request):
        """
        @brief 특정 유저의 팔로우를 취소하는 함수

        @param request Django의 HTTP 요청 객체

        @return
            - 팔로우 취소 성공 : "Unfollow complete" (200)
            - 팔로우가 존재하지 않는 경우 : "Follow relation not found" (404)
            - 기타 예외 발생 : 에러 메시지 (500)
        """
        try:
            user, token_response = authenticate_token(request)
            if token_response:
                return token_response

            body = json.loads(request.body)
            nickname = body.get("name")

            if not nickname:
                return JsonResponse({"message": "Nickname not provided"}, status=400)

            try:
                target_user = User.objects.get(nickname=nickname)
            except User.DoesNotExist:
                return JsonResponse({"message": "User not found"}, status=404)

            follow_relation = Follow.objects.filter(userA=user, userB=target_user)

            if not follow_relation.exists():
                return JsonResponse(
                    {"message": "Follow relation not found"}, status=404
                )

            follow_relation.delete()
            return JsonResponse({"message": "Unfollow complete"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON format"}, status=400)

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)


@swagger_auto_schema(
    method="get",
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "data": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "nickname": openapi.Schema(
                                type=openapi.TYPE_STRING, example="user nickname"
                            ),
                            "imagePath": openapi.Schema(
                                type=openapi.TYPE_STRING, example="user image path(url)"
                            ),
                        },
                    ),
                ),
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
    operation_description="Retrieves the list of users the current user is following.",
    operation_summary="Get follower list",
)
@api_view(["GET"])
def get_follower_list(request):
    """
    @brief 팔로우 하고있는 유저들의 데이터를 요청하는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공 : 팔로우 하고있는 유저들의 데이터 (200)
        - 기타 예외 발생 : 에러 메시지 (500)
    """
    try:
        user, token_response = authenticate_token(request)
        if token_response:
            return token_response

        followers = user.following.all()

        follow_list = []
        for follow in followers:
            if follow.userA == user:
                follow_user = follow.userB

            follow_list.append(
                {"nickname": follow_user.nickname, "imagePath": follow_user.imagePath}
            )
        return JsonResponse({"data": follow_list}, status=200)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
