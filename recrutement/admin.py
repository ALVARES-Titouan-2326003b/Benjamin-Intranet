from django.contrib import admin
from .models import FicheDePoste, Candidat, Candidature

@admin.register(FicheDePoste)
class FicheAdmin(admin.ModelAdmin):
    list_display = ("id", "titre", "created_at")
    search_fields = ("titre", "description", "competences_clees")

@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "email", "uploaded_at")
    search_fields = ("nom", "email", "cv_texte")
 
@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ("id", "fiche", "candidat", "score", "statut", "created_at")
    list_filter = ("statut",)
    search_fields = ("fiche__titre", "candidat__nom", "explication")
