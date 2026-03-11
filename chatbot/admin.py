from django.contrib import admin
from .models import ChatbotQuery


@admin.register(ChatbotQuery)
class ChatbotQueryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "query_type",
        "short_message",
        "created_at",
    )
    list_filter = (
        "query_type",
        "created_at",
    )
    search_fields = (
        "user__username",
        "message",
        "response",
    )
    readonly_fields = (
        "user",
        "query_type",
        "message",
        "response",
        "created_at",
    )
    ordering = ("-created_at",)
    list_per_page = 50
    date_hierarchy = "created_at"

    def short_message(self, obj):
        if not obj.message:
            return "—"
        return obj.message[:80] + ("..." if len(obj.message) > 80 else "")

    short_message.short_description = "Question"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False