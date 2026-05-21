
from django.contrib import admin

from .models import Activite, HistoriqueRappelActivite, NotificationInterne


@admin.register(Activite)
class ActiviteAdmin(admin.ModelAdmin):
    list_display = ("titre", "dossier", "type", "date", "statut", "priorite", "responsable")
    list_filter = ("statut", "priorite", "type")
    search_fields = ("titre", "dossier__reference", "client", "contact_externe")


@admin.register(HistoriqueRappelActivite)
class HistoriqueRappelActiviteAdmin(admin.ModelAdmin):
    list_display = ("activite", "canal", "destinataire", "jours_avant_echeance", "statut", "created_at")
    list_filter = ("canal", "statut", "jours_avant_echeance")
    search_fields = ("activite__titre", "destinataire", "erreur")


@admin.register(NotificationInterne)
class NotificationInterneAdmin(admin.ModelAdmin):
    list_display = ("titre", "user", "activite", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("titre", "message", "user__username")
