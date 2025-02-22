from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    @brief User 모델을 Django Admin에 등록하기 위한 설정
    @details 사용자 정보를 관리하며 목록, 검색, 필터링 기능을 제공

    @list_display 목록에 표시할 필드
    @search_fields 검색할 수 있는 필드
    @list_filter 리스트 필터링 옵션
    """

    list_display = (
        "id",
        "username",
        "email",
        "nickname",
        "winCnt",
        "loseCnt",
        "is_staff",
    )
    search_fields = ("username", "nickname")
    list_filter = ("is_staff", "is_superuser")
