import random
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import redis
from django.utils.timezone import now

User = get_user_model()

redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)


def update_user_last_activity(user_id):
    """
    @brief 유저의 마지막 활동시간 생성 및 갱신 함수

    @param
        - user_id(User의 pk)

    @return
        - 없음

    @detail
        - Redis에 저장된 유저의 마지막 활동시간은 30분 뒤 자동삭제 됩니다.
    """

    timestamp = now().isoformat()
    redis_client.set(f"user:{user_id}", timestamp, ex=1800)


def get_user_last_activity(user_id):
    """
    @brief 유저의 마지막 활동시간 조회 함수

    @param
        - user_id(User의 pk)

    @return
        - 유저의 활동기록이 Redis에 존재할 때 : iso format time
        - 유저의 활동기록이 Redis에 없을 때 : None
    """

    return redis_client.get(f"user:{user_id}")


def authenticate_token(request):
    """
    @brief JWT 검증 함수

    @param request 그대로 넘겨줌.

    @return
        - 성공 : (유저 객체, None) 형식으로 반환
        - 실패 (access_token 만료) : (None, 토큰 갱신 메시지) 형식으로 반환
        - 실패 (refresh_token 만료 or 유효하지 않은 JWT) : (None, 실패 메시지) 형식으로 반환

    @details
    request의 쿠키에서 access_token과 refresh_token을 가져온다.
    access_token을 디코딩하여 user_id를 추출한다.
    access_token의 payload에서 user_id(pk)를 가져온다.
        - access_token이 없거나 만료된 경우, refresh_token을 사용해 새로운 access_token을 생성하고 (None, 토큰 갱신 메시지) 형식으로 반환한다.
        - refresh_token이 만료되었거나 access_token이 유효하지 않으면 (None, 실패 메시지) 형식으로 반환한다.
    추출된 user_id를 기반으로 User 테이블에서 사용자 객체를 찾아서 (User, None) 형식으로 반환한다.
    """
    access_token = request.COOKIES.get("access_token")
    refresh_token = request.COOKIES.get("refresh_token")

    if not access_token and not refresh_token:
        return None, JsonResponse({"message": "JWTs are missing."}, status=401)

    user_id = None

    if access_token:
        try:
            access_payload = AccessToken(access_token)
            user_id = access_payload.get("user_id")
        except TokenError:
            pass

    if not user_id:
        try:
            refresh = RefreshToken(refresh_token)
            new_access = refresh.access_token

            response = JsonResponse({"message": "Token refreshed"}, status=452)
            response.set_cookie(
                key="access_token",
                value=str(new_access),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                path="/",
            )
            return None, response
        except TokenError:
            return None, JsonResponse(
                {"message": "Invalid or expired refresh token"}, status=401
            )

    if not user_id:
        return None, JsonResponse({"message": "Invalid token payload"}, status=401)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None, JsonResponse({"message": "User not found"}, status=401)

    update_user_last_activity(user.id)

    return user, None


def generate_random_nickname():
    """
    @brief 랜덤한 유저 닉네임을 생성하는 함수

    @param 없음

    @return 다른 유저와 중복되지 않는 랜덤 생성된 유저의 닉네임

    @details
    10000 부터 99999 까지의 임의의 수를 무작위로 골라서 '#' 문자열 뒤에 붙인다.
    User 테이블을 조회하여 랜덤 생성된 닉네임의 중복여부를 확인한다.
        - 중복되었다면 새로운 랜덤 닉네임을 다시 생성한다.
        - 중복되지 않았다면 해당 닉네임을 리턴한다.
    최종적으로 중복되지 않은 닉네임을 리턴한다.
    """
    while True:
        random_nickname = str(random.randint(10000, 99999))
        if not User.objects.filter(nickname=random_nickname).exists():
            return random_nickname
