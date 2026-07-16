from django.contrib import admin
from .models import Facture, PieceJointe, Entreprise, InvoiceReminderSettings

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_facture', 'societe', 'affaire', 'fournisseur', 'montant', 'statut', 'service', 'echeance')
    search_fields = ('id', 'numero_facture', 'societe', 'affaire', 'fournisseur__nom', 'titre', 'service')
    list_filter = ('statut', 'service')

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('id', 'facture', 'uploaded_at')

@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom')


@admin.register(InvoiceReminderSettings)
class InvoiceReminderSettingsAdmin(admin.ModelAdmin):
    list_display = ("sender", "updated_at")
    readonly_fields = ("updated_at",)
