from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentTechnique(models.Model):
    TYPE_CHOICES = [
        ("contrat_reservation", "Contrat de réservation"),
        ("permis_construire", "Permis de construire"),
        ("pv", "Procès-verbal"),
        ("autre", "Autre"),
    ]

    projet = models.CharField("Projet", max_length=255, blank=True)
    titre = models.CharField("Titre du document", max_length=255)
    type_document = models.CharField(
        "Type de document",
        max_length=50,
        choices=TYPE_CHOICES,
        default="autre",
    )
    fichier = models.FileField("Fichier", upload_to="documents_tech/")

    texte_brut = models.TextField("Texte extrait", blank=True)
    resume = models.TextField("Résumé global", blank=True)

    prix = models.TextField("Prix / montants", blank=True)
    dates = models.TextField("Dates clés", blank=True)
    conditions_suspensives = models.TextField("Conditions suspensives", blank=True)
    penalites = models.TextField("Pénalités", blank=True)
    delais = models.TextField("Délais", blank=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titre} ({self.projet or 'Sans projet'})"
