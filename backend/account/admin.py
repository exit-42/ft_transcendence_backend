from django.contrib import admin

# Register your models here.

from .models import User, OAuth, LocalAuth, Follow


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    @brief User 모델을 Django Admin에 등록하기 위한 설정
    @details 사용자 정보를 관리하며 목록, 검색, 필터링 기능을 제공

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    @list_filter 리스트 필터링 옵션
    """

    list_display = ("username", "email", "nickname", "winCnt", "loseCnt", "is_staff")
    search_fields = ("username", "nickname")
    list_filter = ("is_staff", "is_superuser")


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


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """
    @brief FollowAdmin 모델을 Django Admin에 등록하기 위한 설정
    @details FollowAdmin 기능을 사용하는 사용자의 인증정보를 관리

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    """

    list_display = ("followId", "userA", "userB", "createdAt")
    search_fields = ("userA__nickname", "userB__nickname")
