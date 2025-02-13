from django.urls import path
from . import views

app_name = "follows"

urlpatterns = [
    path("", views.followView.as_view()),
    path("list/", views.get_follows),
]
