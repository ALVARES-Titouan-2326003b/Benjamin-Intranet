from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentTechnique(models.Model):
    """
    Modèle représentant un document du pôle technique

    Attributes:
        projet (str): Projet de l'entreprise
        titre (str): Titre du document
        type_document (str): Type de document
        fichier (FieldFile): Document PDF
        texte_brut (str): Texte du document
        resume (str): Resumé global
        prix (str): Montant
        dates (str): Dates clés
        conditions_suspensives (str): Conditions suspensives
        penalites (str): Pénalités
        delais (str): Délais
        clauses_importantes (str): Clauses importantes
        created_by (ForeignKey): Utilisateur qui a créé le document
        created_at (datetime): Date de création du document
    """
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
    clauses_importantes = models.TextField("Clauses importantes", blank=True)

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


class TechnicalProject(models.Model):
    """
    Modèle représentant un projet du pôle technique

    Attributes:
        reference (str): Reference du projet
        name (str): Nom du projet
        type (str): Type de dossier
        engaged_amount (Decimal): Frais engagés
        paid_amount (Decimal): Frais payés
        total_estimated (Decimal): Total estimé du projet
    """
    DOSSIER_TYPES = [
        ("client", "Client"),
        ("juridique", "Juridique"),
    ]

    reference = models.CharField("Référence projet", max_length=50, unique=True, db_column='reference')
    name = models.CharField("Nom du projet", max_length=255, db_column='nom')
    type = models.TextField(choices=DOSSIER_TYPES, default="Client")

    # Saisis de l'utilisateur
    engaged_amount = models.DecimalField(
        "Frais engagés",
        max_digits=12,
        decimal_places=2,
        default=0,
        db_column='frais_eng',
    )
    paid_amount = models.DecimalField(
        "Frais déjà payés",
        max_digits=12,
        decimal_places=2,
        default=0,
        db_column='frais_payes',
    )
    total_estimated = models.DecimalField(
        "Total estimé du projet",
        max_digits=12,
        decimal_places=2,
        default=0,
        db_column='total_estim',
    )

    class Meta:
        managed = False
        db_table = 'Dossier'

    def __str__(self):
        return f"{self.reference} - {self.name}"

    @property
    def frais_engages(self):
        """Renvoie les frais engagés du projet"""
        return self.engaged_amount

    @property
    def frais_payes(self):
        """Renvoie les frais payés du projet"""
        return self.paid_amount

    @property
    def frais_restants(self):
        """Renvoie les frais restants du projet"""
        return self.engaged_amount - self.paid_amount

    @property
    def reste_a_engager(self):
        """Renvoie le reste à engager du projet"""
        return self.total_estimated - self.engaged_amount


class ProjectExpense(models.Model):
    project = models.ForeignKey(
        TechnicalProject,
        related_name="expenses",
        on_delete=models.CASCADE,
        verbose_name="Projet",
    )
    label = models.CharField("Libellé", max_length=255)
    amount = models.DecimalField("Montant", max_digits=12, decimal_places=2)
    is_paid = models.BooleanField("Déjà payé", default=False)
    due_date = models.DateField("Échéance", null=True, blank=True)
    payment_date = models.DateField("Date de paiement", null=True, blank=True)

    class Meta:
        verbose_name = "Frais projet"
        verbose_name_plural = "Frais projets"

    def __str__(self):
        return f"{self.project.reference} - {self.label}"