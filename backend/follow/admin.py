from django.contrib import admin

# Register your models here.

from .models import Follow


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
