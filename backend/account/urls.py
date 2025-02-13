from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path("login/", views.login),
    path("logout/", views.logout),
    path("csrf-token/", views.get_csrf_token),
    path("profile/nickname/", views.change_nickname),
    path("profile/image/", views.change_profile_image),
]
