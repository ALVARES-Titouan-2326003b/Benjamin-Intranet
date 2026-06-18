from django.contrib import admin
from .models import ExportCegidRun, Facture, PieceJointe, Entreprise, InvoiceReminderSettings

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('id', 'fournisseur', 'client', 'montant', 'statut', 'service', 'echeance')
    search_fields = ('id', 'fournisseur__nom', 'client__entreprise__nom', 'titre', 'service')
    list_filter = ('statut', 'service')

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('id', 'facture', 'uploaded_at')

@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom')


@admin.register(ExportCegidRun)
class ExportCegidRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'triggered_by', 'line_count', 'total_amount', 'anomaly_count', 'started_at')
    list_filter = ('status',)
    readonly_fields = ('started_at', 'completed_at')


@admin.register(InvoiceReminderSettings)
class InvoiceReminderSettingsAdmin(admin.ModelAdmin):
    list_display = ("sender", "updated_at")
    readonly_fields = ("updated_at",)
