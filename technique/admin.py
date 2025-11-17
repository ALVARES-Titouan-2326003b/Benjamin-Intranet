from django.contrib import admin
from .models import DocumentTechnique


@admin.register(DocumentTechnique)
class DocumentTechniqueAdmin(admin.ModelAdmin):
    list_display = ("id", "titre", "projet", "type_document", "created_at")
    list_filter = ("type_document", "created_at")
    search_fields = ("titre", "projet", "texte_brut")
