from django.contrib import admin
from .models import DocumentTechnique, TechnicalProject, ProjectExpense, TechnicalProjectHistory


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
