from decimal import Decimal
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
        db_table = "document_technique"
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

    reference = models.CharField("Référence projet", max_length=50, unique=True, db_column="reference")
    name = models.CharField("Nom du projet", max_length=255, db_column="nom")
    type = models.TextField(choices=DOSSIER_TYPES, default="client")

    engaged_amount = models.DecimalField(
        "Frais engagés",
        max_digits=12,
        decimal_places=2,
        default=0,
        db_column="frais_eng",
    )
    paid_amount = models.DecimalField(
        "Frais déjà payés",
        max_digits=12,
        decimal_places=2,
        default=0,
        db_column="frais_payes",
    )
    total_estimated = models.DecimalField(
        "Total estimé du projet",
        max_digits=12,
        decimal_places=2,
        default=0,
        db_column="total_estim",
    )

    class Meta:
        db_table = "dossier"

    def __str__(self):
        return f"{self.reference} - {self.name}"

    def refresh_amounts_from_expenses(self, save=True):
        expenses = self.expenses.all()
        engaged = sum((expense.amount for expense in expenses), Decimal("0.00"))
        paid = sum((expense.amount for expense in expenses if expense.is_paid), Decimal("0.00"))

        self.engaged_amount = engaged
        self.paid_amount = paid

        if save:
            self.save(update_fields=["engaged_amount", "paid_amount"])

    @property
    def frais_engages(self):
        return self.engaged_amount

    @property
    def frais_payes(self):
        return self.paid_amount

    @property
    def frais_restants(self):
        return self.engaged_amount - self.paid_amount

    @property
    def reste_a_engager(self):
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
        db_table = "depense_projet"
        verbose_name = "Frais projet"
        verbose_name_plural = "Frais projets"
        ordering = ["due_date", "id"]

    def __str__(self):
        return f"{self.project.reference} - {self.label}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.project.refresh_amounts_from_expenses()

    def delete(self, *args, **kwargs):
        project = self.project
        super().delete(*args, **kwargs)
        project.refresh_amounts_from_expenses()