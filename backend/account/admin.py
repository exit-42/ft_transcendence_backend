from django.contrib import admin

# Register your models here.

from .models import User, OAuth


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "nickname", "winCnt", "loseCnt", "is_staff")
    search_fields = ("username", "email", "nickname")
    list_filter = ("is_staff", "is_superuser")


@admin.register(OAuth)
class OAuthAdmin(admin.ModelAdmin):
    list_display = ("intraId", "user")
    search_fields = ("intraId", "user__username")
