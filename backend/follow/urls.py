from django.urls import path
from . import views

app_name = "follow"

urlpatterns = [
    path("", views.followView.as_view()),
    path("list/", views.get_follower_list),
]
