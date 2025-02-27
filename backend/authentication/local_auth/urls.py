from django.urls import path
from . import views

urlpatterns = [
    path("signin/", views.signin_local_auth),
    path("token/", views.get_local_auth_token),
    path("id/", views.check_local_auth_id),
    path("signup/", views.local_auth_sign_up),
    path("email/", views.send_authentication_email),
    path("code/", views.authenticate_code),
]
