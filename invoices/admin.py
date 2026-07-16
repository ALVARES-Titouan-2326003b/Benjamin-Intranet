from django.contrib import admin
from .models import Facture, PieceJointe, Entreprise, InvoiceReminderSettings, Societe

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_facture', 'societe', 'affaire', 'fournisseur', 'montant', 'statut', 'service', 'echeance')
    search_fields = ('id', 'numero_facture', 'societe__nom', 'affaire', 'fournisseur__nom', 'titre', 'service')
    list_filter = ('statut', 'service')

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('id', 'facture', 'uploaded_at')

@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom')


@admin.register(Societe)
class SocieteAdmin(admin.ModelAdmin):
    list_display = ("nom", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("nom",)


@admin.register(InvoiceReminderSettings)
class InvoiceReminderSettingsAdmin(admin.ModelAdmin):
    list_display = ("sender", "updated_at")
    readonly_fields = ("updated_at",)
