import os, json
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from core.utils import authenticate_token

User = get_user_model()


@api_view(["POST"])
def login(request):
    """
    @brief JWT를 통해 유저 데이터를 불러오는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공 : 유저 데이터 JsonResponse 형식으로 반환
        - 실패 : 에러메시지와 상태코드 JsonResponse 형식으로 반환

    @details JWT 검증 함수(authenticate_token)의 결과가 유효하면 유저 데이터를 반환한다.
    """
    try:
        user, token_response = authenticate_token(request)
        if token_response:
            return token_response

        user_data = {
            "username": user.username,
            "imagePath": user.imagePath,
            "nickname": user.nickname,
            "winCnt": user.winCnt,
            "loseCnt": user.loseCnt,
        }
        return JsonResponse(user_data, status=200)

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


@api_view(["POST"])
def logout(request):
    """
    @brief 쿠키에 저장된 JWT를 삭제하는 함수

    @param request Django의 HTTP 요청 객체

    @return 로그아웃 성공메시지 JsonResponse 형식으로 반환

    @details 유저 브라우저의 쿠키에 저장된 JWT를 삭제한다.
    """
    response = JsonResponse({"message": "logged out successfully."}, status=200)

    access_token = request.COOKIES.get("access_token")
    refresh_token = request.COOKIES.get("refresh_token")

    if access_token:
        response.delete_cookie("access_token", path="/")
    if refresh_token:
        response.delete_cookie("refresh_token", path="/")
    return response


@ensure_csrf_cookie
def get_csrf_token(request):
    """
    @brief 요청할 때마다 새로운 CSRF 토큰을 반환하는 API

    @param request Django의 HTTP 요청 객체

    @return CSRF 토큰을 포함한 JSON 응답
    """
    return JsonResponse({"csrfToken": get_token(request)})


@api_view(["PATCH"])
def change_nickname(request):
    """
    @brief 유저의 nickname을 변경하는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공 : 닉네임 변경 성공 메시지 (200)
        - 기타 예외 발생 : 에러 메시지 (4xx, 500)
    """
    try:
        user, token_response = authenticate_token(request)
        if token_response:
            return token_response

        body = json.loads(request.body)
        new_nickname = body.get("name")

        if not new_nickname:
            return JsonResponse({"message": "Nickname not provided"}, status=400)

        if User.objects.filter(nickname=new_nickname).exists():
            return JsonResponse({"message": "Nickname is already in use"}, status=409)

        user.nickname = new_nickname
        user.save()

        return JsonResponse({"message": "success"}, status=200)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


@api_view(["POST"])
def change_profile_image(request):
    """
    @brief 유저가 업로드 한 이미지를 저장하고 유저의 프로필 이미지를 변경하는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공 : 프로필 이미지 변경 성공 메시지 (201)
        - 기타 예외 발생 : 에러 메시지 (4xx, 500)
    """
    try:
        user, token_response = authenticate_token(request)
        if token_response:
            return token_response

        if "profile_image" not in request.FILES:
            return JsonResponse({"message": "No file provided"}, status=400)

        image = request.FILES["profile_image"]

        allowed_extensions = [".jpg", ".jpeg", ".png"]
        _, ext = os.path.splitext(image.name)
        ext = ext.lower()

        if ext not in allowed_extensions:
            return JsonResponse(
                {"message": "Invalid file type. Only JPG, JPEG, PNG allowed."},
                status=400,
            )

        front_server_url = os.environ.get("FRONT_SERVER_URL", "").rstrip("/")
        default_image_url = f"{front_server_url}/static/image/default.jpeg"

        if user.imagePath and user.imagePath != default_image_url:
            if user.imagePath.startswith(front_server_url):
                old_image_path = user.imagePath.replace(front_server_url, "").lstrip(
                    "/"
                )
            else:
                old_image_path = user.imagePath.replace("/media/", "")

            old_image_path = old_image_path.replace("media/", "", 1)

            if default_storage.exists(old_image_path):
                try:
                    default_storage.delete(old_image_path)
                except Exception as e:
                    return JsonResponse(
                        {"message": f"Error deleting old file: {str(e)}"}, status=500
                    )

        file_name = f"{user.username}{ext}"
        file_path = os.path.join("profile_images", file_name)

        saved_path = default_storage.save(file_path, ContentFile(image.read()))
        image_url = f"{front_server_url}/media/{saved_path}"

        user.imagePath = image_url
        user.save()

        return JsonResponse({"message": "Image change success"}, status=201)

    except KeyError:
        return JsonResponse({"message": "Missing required fields"}, status=400)

    except Exception as e:
        return JsonResponse({"message": f"Unexpected error: {str(e)}"}, status=500)
