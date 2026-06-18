from django.contrib import admin
from .models import (
    DocumentTechnique,
    TechnicalEmail,
    TechnicalEmailAttachment,
    TechnicalProject,
    ProjectExpense,
    TechnicalProjectHistory,
)


@admin.register(DocumentTechnique)
class DocumentTechniqueAdmin(admin.ModelAdmin):
    list_display = ("id", "titre", "projet", "type_document", "created_by", "created_at")
    list_filter = ("type_document", "created_at")
    search_fields = ("titre", "projet", "texte_brut", "resume")


class ProjectExpenseInline(admin.TabularInline):
    model = ProjectExpense
    extra = 0


@admin.register(TechnicalProject)
class TechnicalProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "reference", "name", "type", "engaged_amount", "paid_amount", "total_estimated")
    list_filter = ("type",)
    search_fields = ("reference", "name")
    inlines = [ProjectExpenseInline]


@admin.register(ProjectExpense)
class ProjectExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "facture", "label", "amount", "is_paid", "due_date", "payment_date")
    list_filter = ("is_paid", "due_date", "payment_date")
    search_fields = ("label", "project__reference", "project__name", "facture__id")


@admin.register(TechnicalProjectHistory)
class TechnicalProjectHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "project_reference", "action", "target_type", "target_label", "user", "created_at")
    list_filter = ("action", "target_type", "created_at")
    search_fields = ("project_reference", "project_name", "target_label", "user__username")
    readonly_fields = ("project", "project_reference", "project_name", "user", "action", "target_type", "target_label", "before", "after", "created_at")


class TechnicalEmailAttachmentInline(admin.TabularInline):
    model = TechnicalEmailAttachment
    extra = 0
    readonly_fields = (
        "original_name",
        "content_type",
        "size",
        "processing_status",
        "processing_error",
        "linked_document",
        "processed_at",
    )


@admin.register(TechnicalEmail)
class TechnicalEmailAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "sender", "project", "status", "received_at")
    list_filter = ("status", "has_attachments", "received_at")
    search_fields = ("subject", "sender", "external_id", "thread_id")
    inlines = [TechnicalEmailAttachmentInline]


@admin.register(TechnicalEmailAttachment)
class TechnicalEmailAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_name",
        "email",
        "processing_status",
        "linked_document",
        "processed_at",
    )
    list_filter = ("processing_status", "content_type", "processed_at")
    search_fields = ("original_name", "email__subject", "processing_error")
