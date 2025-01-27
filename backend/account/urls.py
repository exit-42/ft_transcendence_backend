from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path("oauth/token/", views.get_oauth_token),
    path("oauth/callback/", views.callback),
    path("local-auth/token/", views.get_local_auth_token),
    path("local-auth/id/", views.check_local_auth_id),
    path("local-auth/signup/", views.local_auth_sign_up),
    path("local-auth/email/", views.send_authentication_email),
    path("local-auth/code/", views.authenticate_code),
    path("login/", views.login),
]
