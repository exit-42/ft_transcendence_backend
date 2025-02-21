from django.urls import path
from . import views

app_name = "log"

urlpatterns = [
    # path("", views.logView.as_view()),
    path("match/", views.create_match_log),
    path("", views.get_game_logs),
]
