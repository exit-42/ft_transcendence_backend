from django.urls import path
from . import views

urlpatterns = [
    path("token/", views.get_oauth_token),
    path("callback/", views.callback),
]
