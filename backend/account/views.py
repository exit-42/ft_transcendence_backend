import os, requests, random, json
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from django.contrib.auth.hashers import make_password, check_password

User = get_user_model()

from account.models import OAuth, LocalAuth


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


@api_view(["POST"])
def get_local_auth_token(request):
    """
    @brief LocalAuth 회원에게 JWT를 발급하는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공: JWT를 생성하여 사용자의 쿠키에 저장하고 기본 페이지(localhost)로 리디렉션
        - 실패: 상태 코드와 에러 메시지를 JSON 형태로 반환

    @details
    Request의 바디에서 id와 password를 추출한다.
    LocalAuth 테이블에서 입력받은 id와 동일한 localId를 가진 객체가 존재하는지 확인한다.
    - 일치하는 객체가 없는 경우 에러메시지를 JsonResponse 형태로 리턴한다.
    - 일치하는 객체가 있는 경우 입력받은 password와 localPassword가 일치하는지 확인한다.
        - 일치하는 객체가 없는 경우 에러메시지를 JsonResponse 형태로 리턴한다.
        - 일치하는 객체가 있는 경우 유저 객체를 통해 JWT를 생성하여 사용자의 클라이언트 쿠키에 access_token과 refresh_token을 저장한다.
          성공메시지를 JsonResponse 형태로 리턴한다.
    """
    try:
        data = json.loads(request.body)
        local_id = data.get("id")
        local_password = data.get("password")
        if not local_id or not local_password:
            return JsonResponse(
                {"error": "Please provide id and password. Both are required."},
                status=400,
            )
        try:
            local_auth = LocalAuth.objects.get(localId=local_id)
        except LocalAuth.DoesNotExist:
            return JsonResponse({"error": "id not exist."}, status=404)
        if not check_password(local_password, local_auth.localPassword):
            return JsonResponse({"error": "wrong password."}, status=401)
        user = local_auth.user
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        response = JsonResponse({"message": "success"}, status=200)
        response.set_cookie(
            key="access_token",
            value=str(access),
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
            path="/",
        )
        return response
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Please send the data in JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse({"error": f"{str(e)}"}, status=500)


@api_view(["GET"])
def check_local_auth_id(request):
    """
    @brief 특정 ID를 가진 LocalAuth 객체가 존재하는지 확인하는 함수

    @param request Django의 HTTP 요청 객체

    @return ID 중복여부를 상태코드와 JSON 형태로 반환

    @details
    URL 쿼리 스트링에서 local_id를 추출한다.
    LocalAuth 테이블에 local_id와 동일한 localID를 가진 객체가 존재하는지 확인한다.
    """
    try:
        local_id = request.GET.get("id")
        if not local_id:
            return JsonResponse({"error": "ID not provided."}, status=400)

        if LocalAuth.objects.filter(localId=local_id).exists():
            return JsonResponse({"error": "ID already in use"}, status=409)
        else:
            return JsonResponse(
                {"message": "ID is available", "id": local_id}, status=200
            )
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)


@api_view(["POST"])
def local_auth_sign_up(request):
    """
    @brief LocalAuth 회원가입 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공: 상태 코드를 JSON 형태로 반환
        - 실패: 상태 코드와 에러 메시지를 JSON 형태로 반환

    @details
    Request의 바디에서 id와 password를 추출한다.
    LocalAuth 테이블에서 입력받은 id와 동일한 localId를 가진 객체가 존재하는지 확인한다.
        - 일치하는 객체가 있는 경우 에러메시지를 JsonResponse 형태로 리턴한다.
        - 일치하는 객체가 없는 경우 입력받은 값으로 유저를 생성하고 상태코드를 JsonResponse 형태로 리턴한다.
    """
    try:
        data = json.loads(request.body)
        local_id = data.get("id")
        local_password = data.get("password")
        user_email = data.get("email")

        if not local_id or not local_password or not user_email:
            return JsonResponse({"error": "All fields are required."}, status=400)

        if LocalAuth.objects.filter(localId=local_id).exists():
            return JsonResponse({"error": "ID already in use"}, status=409)

        random_nickname = generate_random_nickname()
        user = User.objects.create(
            email=user_email,
            imagePath="http://localhost/static/image/default.jpeg",
            nickname=random_nickname,
        )
        hashed_password = make_password(local_password)
        LocalAuth.objects.create(
            user=user, localId=local_id, localPassword=hashed_password
        )
        return JsonResponse({"message": "Sign-up success!"}, status=201)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Please send the data in JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse({"error": f"{str(e)}"}, status=500)
