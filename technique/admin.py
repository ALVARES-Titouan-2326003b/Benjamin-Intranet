from django.contrib import admin
from .models import DocumentTechnique, TechnicalProject, ProjectExpense


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
