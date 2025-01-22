from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path("oauth/token/", views.get_oauth_token),
    path("oauth/callback/", views.callback),
    path("local-auth/token/", views.get_local_auth_token),
]
