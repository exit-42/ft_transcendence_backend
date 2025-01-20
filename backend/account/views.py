import os, requests, random
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view

User = get_user_model()

from account.models import OAuth


@api_view(["GET"])
def get_oauth_token(request):
    """
    @brief 클라이언트를 42 API의 OAuth 인증 페이지로 리디렉션하는 함수

    @param request Django의 HTTP 요청 객체

    @return 42 API의 OAuth 인증 페이지로 리디렉션

    @details
    환경 변수에서 CLIENT_ID와 REDIRECT_URI를 읽어와 OAuth 인증 URL을 생성합니다.
    생성된 URL로 리디렉션하여 42 인증을 시작합니다.
    """

    client_id = os.environ.get("CLIENT_ID")
    redirect_uri = os.environ.get("REDIRECT_URI")
    authorize_uri = f"https://api.intra.42.fr/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=public"
    return redirect(authorize_uri)


def callback(request):
    """
    @brief 42 OAuth 인증 콜백을 처리하는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공: JWT를 생성하여 사용자의 쿠키에 저장하고 기본 페이지(localhost)로 리디렉션
        - 실패: 상태 코드와 에러 메시지를 JSON 형태로 반환

    @details
    42 API 서버로부터 받은 인증 코드를 사용하여 access_token 및 refresh_token을 요청한다.
    access_token을 이용하여 42 API 서버에서 사용자 정보를 가져온다.
    가져온 사용자 정보(인트라 ID, 이메일, 프로필 이미지 url)를 기반으로
    OAuth 테이블에서 해당 사용자를 조회하여
        - 동일한 유저가 없으면 새 사용자 정보를 데이터베이스에 저장하고 유저 객체를 통해
        - 동일한 유저가 있으면 해당 유저 객체를 통해
    JWT를 생성하여 사용자의 클라이언트 쿠키에 access_token과 refresh_token을 저장한다.
    이후 사용자를 기본 페이지(http://localhost)로 리디렉션한다.
    """
    code = request.GET.get("code")
    if not code:
        return JsonResponse(
            {
                "error": "No authorization code in request",
            },
            status=400,
        )
    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")
    redirect_uri = os.environ.get("REDIRECT_URI")
    token_url = "https://api.intra.42.fr/oauth/token"
    token_response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    if token_response.status_code == 200:
        access_token = token_response.json().get("access_token")
        user_info = requests.get(
            "https://api.intra.42.fr/v2/me",
            headers={"Authorization": f"Bearer {access_token}"},
        ).json()
        intra_id = user_info.get("login")
        user_email = user_info.get("email")
        user_image_path = user_info.get("image", {}).get("link")
        user, created = get_or_create_user_oauth(intra_id, user_email, user_image_path)
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        response = HttpResponseRedirect("http://localhost")
        response.set_cookie(
            key="access_token",
            value=str(access),
            httponly=True,
            secure=False,  # 나중에 True로 변경
            samesite="Lax",
            max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=False,  # 나중에 True로 변경
            samesite="Lax",
            max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
            path="/",
        )
        return response
    else:
        return JsonResponse(
            {
                "error": "Token Request Failed",
            },
            status=token_response.status_code,
        )


def generate_random_nickname():
    """
    @brief 랜덤한 유저 닉네임을 생성하는 함수

    @param 없음

    @return 다른 유저와 중복되지 않는 랜덤 생성된 유저의 닉네임

    @details
    10000 부터 99999 까지의 임의의 수를 무작위로 골라서 'USER#' 문자열 뒤에 붙인다.
    User 테이블을 조회하여 랜덤 생성된 닉네임의 중복여부를 확인한다.
        - 중복되었다면 새로운 랜덤 닉네임을 다시 생성한다.
        - 중복되지 않았다면 해당 닉네임을 리턴한다.
    최종적으로 중복되지 않은 닉네임을 리턴한다.
    """
    while True:
        random_number = f"{random.randint(10000, 99999):05}"  # 5자리 숫자 생성
        nickname = f"USER#{random_number}"
        if not User.objects.filter(nickname=nickname).exists():  # 중복 확인
            return nickname


def get_or_create_user_oauth(intra_id, user_email, user_image_path):
    """
    @brief OAuth 인증을 통해 유저를 조회하거나 생성하는 함수

    @param
        - intra_id : 유저의 42 인트라 아이디
        - user_email : 유저의 이메일
        - user_image_path : 유저의 사진 url

    @return 유저(user)와 생성 여부(bool created)

    @details
    OAuth 테이블에서 유저의 인트라아이디와 동일한 인트라아이디를 가진 객체가 있는지 탐색한다.
        - 동일한 인트라 아이디를 가진 유저가 있다면 해당 유저와 생성 여부(false)를 리턴한다.
        - 동일한 인트라 아이디를 가진 유저가 없다면 새롭게 유저 객체를 생성하고 연결된 OAuth 객체를 생성하여 해당 유저와 생성 여부(true)를 리턴한다.
    """
    try:
        oauth_account = OAuth.objects.filter(intraId=intra_id).first()
        if oauth_account:
            user = oauth_account.user
            created = False
        else:
            random_nickname = generate_random_nickname()
            user, created = User.objects.get_or_create(
                email=user_email,
                defaults={
                    "imagePath": user_image_path,
                    "nickname": random_nickname,
                },
            )
            if created:
                OAuth.objects.create(user=user, intraId=intra_id)
        return user, created
    except Exception as e:
        return None, False
