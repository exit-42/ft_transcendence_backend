from django.contrib import admin

from .models import OAuth, LocalAuth


@admin.register(OAuth)
class OAuthAdmin(admin.ModelAdmin):
    """
    @brief OAuth 모델을 Django Admin에 등록하기 위한 설정
    @details OAuth 기능을 사용하는 사용자의 인증정보를 관리

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    """

    list_display = ("intraId", "user")
    search_fields = ("intraId", "user__nickname")


@admin.register(LocalAuth)
class LocalAuthAdmin(admin.ModelAdmin):
    """
    @brief LocalAuth 모델을 Django Admin에 등록하기 위한 설정
    @details LocalAuth 기능을 사용하는 사용자의 인증정보를 관리

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    """

    list_display = ("localId", "user")
    search_fields = ("localId", "user__nickname")
