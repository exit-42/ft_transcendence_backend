import os
from django.shortcuts import redirect
from django.http import HttpResponse
from rest_framework.decorators import api_view

# Create your views here.


@api_view(["GET"])
def get_oauth_token(request):
    client_id = os.environ.get("CLIENT_ID")
    redirect_uri = os.environ.get("REDIRECT_URI")
    authorize_uri = f"https://api.intra.42.fr/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=public"
    return redirect(authorize_uri)
