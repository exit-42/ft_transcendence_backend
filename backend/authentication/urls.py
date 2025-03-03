from django.urls import path, include
from authentication.oauth import views
from authentication.local_auth import views

app_name = "authentication"

urlpatterns = [
    path("oauth/", include("authentication.oauth.urls")),
    path("local-auth/", include("authentication.local_auth.urls")),
]
