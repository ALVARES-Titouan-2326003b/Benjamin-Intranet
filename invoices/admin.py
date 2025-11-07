from django.contrib import admin
from .models import Facture, PieceJointe, Entreprise

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('id', 'fournisseur', 'client', 'montant', 'statut', 'echeance')
    search_fields = ('id', 'fournisseur', 'client__nom', 'titre')
    list_filter = ('statut',)

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('id', 'facture', 'uploaded_at')

@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom')
