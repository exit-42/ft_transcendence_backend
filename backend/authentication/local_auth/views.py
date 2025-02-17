import os, random, json
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, parser_classes
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from core.utils import generate_random_nickname

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()

from authentication.models import LocalAuth


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "id": openapi.Schema(
                type=openapi.TYPE_STRING, description="user's login id"
            ),
            "password": openapi.Schema(
                type=openapi.TYPE_STRING, description="user's login password"
            ),
        },
        required=["id", "password"],
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Email has been sent."
                ),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Please provide id and password. Both are required.",
                )
            },
        ),
        401: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="wrong password."
                )
            },
        ),
        404: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="id not exist."
                )
            },
        ),
        500: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Failed to send email"
                )
            },
        ),
    },
)
@api_view(["POST"])
def signin_local_auth(request):
    """
    @brief LocalAuth를 통해 로그인 하는 함수

    @param
        - local_id : LocalAuth 로그인에 필요한 아이디
        - local_password : LocalAuth 로그인에 필요한 비밀번호

    @return
        - 아이디, 비밀번호 일치 : "Email has been sent.", user_email (200)
        - 아이디 발견 실패 : "id not exist." (404)
        - 비밀번호 불일치 : "wrong password." (401)
        - 기타 예외 발생 : 에러 메시지 (500)

    @details
        - 입력받은 아이디와 동일한 아이디를 가진 객체가 LocalAuth에 존재하는지 확인합니다.
        - 특정 객체가 LocalAuth에 존재한다면 입력받은 비밀번호가 해당 객체의 비밀번호와 일치하는지 확인합니다.
        - 아이디와 비밀번호가 모두 일치한다면 해당 유저의 등록된 이메일로 확인 이메일(2FA)을 전송합니다.
    """
    try:
        data = json.loads(request.body)
        local_id = data.get("id")
        local_password = data.get("password")
        if not local_id or not local_password:
            return JsonResponse(
                {"message": "Please provide id and password. Both are required."},
                status=400,
            )
        try:
            local_auth = LocalAuth.objects.get(localId=local_id)
        except LocalAuth.DoesNotExist:
            return JsonResponse({"message": "id not exist."}, status=404)
        if not check_password(local_password, local_auth.localPassword):
            request.session.pop("user_id", None)
            return JsonResponse({"message": "wrong password."}, status=401)
        user = local_auth.user
        random_code = str(random.randint(10000, 99999))
        request.session["user_id"] = user.id
        request.session["authenticate_code"] = random_code
        try:
            send_mail(
                subject="Your 2FA Code",
                message=f"Your 2FA code is: {random_code}",
                from_email=os.environ.get("EMAIL_HOST_USER"),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return JsonResponse({"message": "Failed to send email"}, status=500)
        return JsonResponse(
            {"message": "Email has been sent.", "email": user.email}, status=200
        )
    except Exception as e:
        return JsonResponse({"message": f"{str(e)}"}, status=500)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "code": openapi.Schema(
                type=openapi.TYPE_STRING, description="email 2FA code"
            ),
        },
        required=["code"],
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Invalid code or email."
                )
            },
        ),
        401: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="User not found"
                )
            },
        ),
        404: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Session data is missing or expired.",
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
@api_view(["POST"])
def get_local_auth_token(request):
    """
    @brief LocalAuth 로그인 할 때 2FA 인증을 처리하는 함수

    @param
        - code : 2FA 인증코드

    @return
        - 인증성공(토큰발급) : "success" (200)
        - 세션 관련 에러 발생 : 에러 메시지 (4xx)
        - 기타 예외 발생 : 에러 메시지 (500)
    """
    try:
        data = json.loads(request.body)
        authenticate_code = data.get("code")
        if not authenticate_code:
            return JsonResponse({"message": "Code is required."}, status=400)

        stored_user_id = request.session.get("user_id")
        stored_code = request.session.get("authenticate_code")
        del request.session["user_id"]
        del request.session["authenticate_code"]

        if not stored_user_id or not stored_code:
            return JsonResponse(
                {"message": "Session data is missing or expired."}, status=404
            )

        if stored_code == authenticate_code:
            try:
                user = User.objects.get(id=stored_user_id)
            except User.DoesNotExist:
                return JsonResponse({"message": "User not found"}, status=401)

            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            response = JsonResponse({"message": "success"}, status=200)

            response.set_cookie(
                key="access_token",
                value=str(access),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                path="/",
            )
            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                path="/",
            )
            return response
        else:
            return JsonResponse({"message": "Invalid code or email."}, status=400)
    except json.JSONDecodeError:
        return JsonResponse(
            {"message": "Please send the data in JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse({"message": f"{str(e)}"}, status=500)


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "id", openapi.IN_QUERY, description="login id", type=openapi.TYPE_STRING
        )
    ],
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="ID is available"
                ),
                "id": openapi.Schema(type=openapi.TYPE_STRING, example="login id"),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="ID not provided."
                )
            },
        ),
        409: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="ID already in use"
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
            return JsonResponse({"message": "ID not provided."}, status=400)

        if LocalAuth.objects.filter(localId=local_id).exists():
            return JsonResponse({"message": "ID already in use"}, status=409)
        else:
            return JsonResponse(
                {"message": "ID is available", "id": local_id}, status=200
            )
    except Exception as e:
        return JsonResponse({"message": f"Server error: {str(e)}"}, status=500)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, description="user email address"
            ),
        },
        required=["email"],
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Email has been sent."
                ),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Email is required."
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
@api_view(["POST"])
def send_authentication_email(request):
    """
    @brief 인증 이메일 전송 함수

    @param request Django의 HTTP 요청 객체

    @return 이메일 전송 성공여부를 상태코드와 JSON 형태로 반환

    @details
    Request의 바디에서 user_email을 추출.
    랜덤 인증 코드를 생성.
    세션에 다음 정보를 저장:
        - authenticate_code: 생성된 인증 코드
        - authenticate_email: 사용자 이메일
        - is_authenticated: False
    user_email으로 랜덤 인증 코드를 전송.
    이메일 전송 성공여부를 반환.
    """
    try:
        data = json.loads(request.body)
        user_email = data.get("email")

        if not user_email:
            return JsonResponse({"message": "Email is required."}, status=400)

        random_code = str(random.randint(10000, 99999))
        request.session["authenticate_code"] = random_code
        request.session["authenticate_email"] = user_email
        request.session["is_authenticated"] = False

        send_mail(
            subject="Your Authentication Code",
            message=f"Your authentication code is: {random_code}",
            from_email=os.environ.get("EMAIL_HOST_USER"),
            recipient_list=[user_email],
            fail_silently=False,
        )
        return JsonResponse({"message": "Email has been sent."}, status=200)

    except json.JSONDecodeError:
        return JsonResponse(
            {"message": "Please send the data in JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse({"message": f"{str(e)}"}, status=500)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, description="user email address"
            ),
            "code": openapi.Schema(
                type=openapi.TYPE_STRING, description="email 2FA code"
            ),
        },
        required=["email"],
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Authentication successful."
                ),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Invalid code or email."
                )
            },
        ),
        404: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Session data is missing or expired.",
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
@api_view(["POST"])
def authenticate_code(request):
    """
    @brief 인증 코드를 검증하고 세션의 인증 상태를 업데이트하는 함수

    @param request Django의 HTTP 요청 객체

    @return
        - 성공: 세션의 인증 상태를 True로 설정하고 성공메시지 반환
        - 실패: 상태 코드와 에러메시지 반환

    @detail
    Request의 바디에서 user_email과 인증 코드(code)를 추출.
    세션에 저장된 이메일과 입력받은 user_email이 동일한지 검사.
    세션에 저장된 인증코드와 입력받은 인증코드가 동일한지 검사.
        - 동일하지 않다면 에러메시지를 JSON 형태로 반환.
        - 동일하다면 세션의 is_authenticated 값을 True로 바꾸고 성공메시지를 JSON 형태로 반환.
    """
    try:
        data = json.loads(request.body)
        authenticate_email = data.get("email")
        authenticate_code = data.get("code")

        if not authenticate_email:
            return JsonResponse({"message": "Email is required."}, status=400)

        if not authenticate_code:
            return JsonResponse({"message": "Code is required."}, status=400)

        stored_code = request.session.get("authenticate_code")
        stored_email = request.session.get("authenticate_email")

        if not stored_code or not stored_email:
            return JsonResponse(
                {"message": "Session data is missing or expired."}, status=404
            )

        if stored_code == authenticate_code and stored_email == authenticate_email:
            request.session["is_authenticated"] = True
            return JsonResponse({"message": "Authentication successful."}, status=200)
        else:
            return JsonResponse({"message": "Invalid code or email."}, status=400)

    except json.JSONDecodeError:
        return JsonResponse(
            {"message": "Please send the data in JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse({"message": f"{str(e)}"}, status=500)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "id": openapi.Schema(
                type=openapi.TYPE_STRING, description="user's login id"
            ),
            "password": openapi.Schema(
                type=openapi.TYPE_STRING, description="user's login password"
            ),
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, description="user email address"
            ),
        },
        required=["id", "password", "email"],
    ),
    responses={
        201: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Sign-up success!"
                ),
            },
        ),
        400: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="All fields are required."
                )
            },
        ),
        403: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="Email verification is required."
                )
            },
        ),
        409: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, example="ID already in use"
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
        - 일치하는 객체가 없는 경우 이메일 인증여부를 확인한다.
            - 이메일 인증을 확인한 후 입력받은 값으로 유저를 생성하고 상태코드를 JSON 형태로 리턴한다.
    """
    try:
        data = json.loads(request.body)
        local_id = data.get("id")
        local_password = data.get("password")
        user_email = data.get("email")

        if not local_id or not local_password or not user_email:
            return JsonResponse({"message": "All fields are required."}, status=400)

        if LocalAuth.objects.filter(localId=local_id).exists():
            return JsonResponse({"message": "ID already in use"}, status=409)

        stored_email = request.session.get("authenticate_email")
        is_authenticated = request.session.get("is_authenticated")

        if stored_email != user_email or not is_authenticated:
            return JsonResponse(
                {"message": "Email verification is required."}, status=403
            )
        random_nickname = generate_random_nickname()
        user = User.objects.create(
            email=user_email,
            imagePath=os.environ.get("FRONT_SERVER_URL") + "/static/image/default.jpeg",
            nickname=random_nickname,
        )
        hashed_password = make_password(local_password)
        LocalAuth.objects.create(
            user=user, localId=local_id, localPassword=hashed_password
        )
        del request.session["authenticate_email"]
        del request.session["authenticate_code"]
        del request.session["is_authenticated"]
        return JsonResponse({"message": "Sign-up success!"}, status=201)

    except json.JSONDecodeError:
        return JsonResponse(
            {"message": "Please send the data in JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse({"message": f"{str(e)}"}, status=500)
