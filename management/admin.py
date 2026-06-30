
from django.contrib import admin

from .models import (
    Activite,
    AdministrativeProject,
    CategorieDossierAdministratif,
    HistoriqueRappelActivite,
    NotificationInterne,
    RegleRappelActivite,
    GmailConversation,
    GmailConversationEvent,
)


@admin.register(CategorieDossierAdministratif)
class CategorieDossierAdministratifAdmin(admin.ModelAdmin):
    list_display = ("nom", "is_default", "created_at")
    list_filter = ("is_default",)
    search_fields = ("nom",)


@admin.register(AdministrativeProject)
class AdministrativeProjectAdmin(admin.ModelAdmin):
    list_display = ("reference", "affaire", "type_dossier", "activite_metier", "etat", "categorie", "prix")
    list_filter = ("type_dossier", "activite_metier", "etat", "categorie", "created_at")
    search_fields = ("reference", "affaire", "name", "adresse_bien", "vendeur", "beneficiaire", "locataire")


@admin.register(Activite)
class ActiviteAdmin(admin.ModelAdmin):
    list_display = ("titre", "dossier", "type", "date", "statut", "priorite", "responsable")
    list_filter = ("statut", "priorite", "type")
    search_fields = ("titre", "dossier__reference")


@admin.register(HistoriqueRappelActivite)
class HistoriqueRappelActiviteAdmin(admin.ModelAdmin):
    list_display = ("activite", "canal", "destinataire", "jours_avant_echeance", "statut", "created_at")
    list_filter = ("canal", "statut", "jours_avant_echeance")
    search_fields = ("activite__titre", "destinataire", "erreur")


@admin.register(RegleRappelActivite)
class RegleRappelActiviteAdmin(admin.ModelAdmin):
    list_display = ("label", "timing", "days", "is_active", "created_at")
    list_filter = ("timing", "is_active")


@admin.register(NotificationInterne)
class NotificationInterneAdmin(admin.ModelAdmin):
    list_display = ("titre", "user", "activite", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("titre", "message", "user__username")


@admin.register(GmailConversation)
class GmailConversationAdmin(admin.ModelAdmin):
    list_display = ("subject", "owner", "recipient", "status", "sent_at", "last_synced_at")
    list_filter = ("status", "sent_at")
    search_fields = ("subject", "recipient", "thread_id")


@admin.register(GmailConversationEvent)
class GmailConversationEventAdmin(admin.ModelAdmin):
    list_display = ("conversation", "event_type", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("conversation__subject", "note", "external_message_id")
    readonly_fields = (
        "conversation",
        "event_type",
        "user",
        "old_status",
        "new_status",
        "note",
        "external_message_id",
        "created_at",
    )
