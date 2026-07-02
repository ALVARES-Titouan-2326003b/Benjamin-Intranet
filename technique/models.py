from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentTechnique(models.Model):
    """
    Modèle représentant un document du pôle technique

    Attributes:
        project (ForeignKey): Dossier technique associé
        titre (str): Titre du document
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
    project = models.ForeignKey(
        "TechnicalProject",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
        verbose_name="Dossier associé",
    )
    titre = models.CharField("Titre du document", max_length=255)
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
        User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        db_table = "document_technique"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titre} ({self.project or 'Sans dossier'})"


class TechnicalProject(models.Model):
    """
    Modèle représentant un dossier du pôle technique

    Attributes:
        reference (str): Reference du dossier
        name (str): Nom du dossier
        type (str): Type de dossier
        status (str): Statut d'avancement du dossier
        engaged_amount (Decimal): Frais engagés
        paid_amount (Decimal): Frais payés
        total_estimated (Decimal): Total estimé du dossier
    """
    DOSSIER_TYPES = [
        ("marchands_de_bien", "Marchands de bien"),
        ("promotion", "Promotion"),
        ("patrimoine", "Patrimoine")
    ]
    STATUS_CHOICES = [
        ("etude", "Étude"),
        ("promesse_signee", "Promesse signée"),
        ("acquis", "Acquis"),
    ]

    reference = models.CharField("Référence dossier", max_length=50, unique=True, db_column="reference")
    name = models.CharField("Nom du dossier", max_length=255, db_column="nom")
    type = models.TextField("Type", choices=DOSSIER_TYPES, default="marchands_de_bien")
    status = models.CharField("Statut", max_length=30, choices=STATUS_CHOICES, default="etude", db_column="statut")
    engaged_amount = models.DecimalField("Frais engagés", max_digits=12, decimal_places=2, default=0, db_column="frais_eng")
    paid_amount = models.DecimalField("Frais déjà payés", max_digits=12, decimal_places=2, default=0, db_column="frais_payes")
    total_estimated = models.DecimalField("Total estimé du dossier", max_digits=12, decimal_places=2, default=0, db_column="total_estim")

    class Meta:
        db_table = "dossier"
        verbose_name = "Dossier technique"
        verbose_name_plural = "Dossiers techniques"

    def __str__(self):
        return f"{self.reference} - {self.name}"

    def refresh_amounts_from_expenses(self, save=True):
        expenses = self.expenses.all()
        engaged = sum((e.amount for e in expenses), Decimal("0.00"))
        paid = sum((e.amount for e in expenses if e.is_paid), Decimal("0.00"))
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
    project = models.ForeignKey(TechnicalProject, related_name="expenses", on_delete=models.CASCADE, verbose_name="Dossier")
    facture = models.OneToOneField(
        "invoices.Facture",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_expense",
        verbose_name="Facture associée",
    )
    label = models.CharField("Libellé", max_length=255)
    amount = models.DecimalField("Montant", max_digits=12, decimal_places=2)
    is_paid = models.BooleanField("Déjà payé", default=False)
    due_date = models.DateField("Échéance", null=True, blank=True)
    payment_date = models.DateField("Date de paiement", null=True, blank=True)

    class Meta:
        db_table = "depense_projet"
        verbose_name = "Frais dossier"
        verbose_name_plural = "Frais dossiers"
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


class TechnicalProjectAction(models.Model):
    STATUS_CHOICES = [
        ("todo", "À faire"),
        ("in_progress", "En cours"),
        ("done", "Terminé"),
        ("cancelled", "Annulé"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Basse"),
        ("normal", "Normale"),
        ("high", "Haute"),
        ("urgent", "Urgente"),
    ]

    project = models.ForeignKey(
        TechnicalProject,
        related_name="actions",
        on_delete=models.CASCADE,
        verbose_name="Dossier",
    )
    title = models.CharField("Action", max_length=255)
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_actions_assigned",
        verbose_name="Assigné à",
    )
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField("Priorité", max_length=20, choices=PRIORITY_CHOICES, default="normal")
    description = models.TextField("Description", blank=True)
    due_date = models.DateField("Échéance", null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_actions_created",
        verbose_name="Créé par",
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_actions_updated",
        verbose_name="Modifié par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        db_table = "technical_project_action"
        ordering = ["due_date", "priority", "id"]
        verbose_name = "Action dossier technique"
        verbose_name_plural = "Actions dossiers techniques"

    def __str__(self):
        return f"{self.project.reference} - {self.title}"


class TechnicalProjectKeyDate(models.Model):
    STATUS_CHOICES = [
        ("planned", "Prévue"),
        ("done", "Réalisée"),
        ("postponed", "Reportée"),
        ("cancelled", "Annulée"),
    ]

    project = models.ForeignKey(
        TechnicalProject,
        related_name="key_dates",
        on_delete=models.CASCADE,
        verbose_name="Dossier",
    )
    label = models.CharField("Libellé", max_length=255)
    date = models.DateField("Date")
    comment = models.TextField("Commentaire", blank=True)
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, blank=True)
    document = models.ForeignKey(
        DocumentTechnique,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="key_dates",
        verbose_name="Document lié",
    )
    action = models.ForeignKey(
        TechnicalProjectAction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="key_dates",
        verbose_name="Action liée",
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_key_dates_created",
        verbose_name="Créé par",
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_key_dates_updated",
        verbose_name="Modifié par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        db_table = "technical_project_key_date"
        ordering = ["date", "id"]
        verbose_name = "Date clé dossier technique"
        verbose_name_plural = "Dates clés dossiers techniques"

    def __str__(self):
        return f"{self.project.reference} - {self.label}"


class TechnicalProjectHistory(models.Model):
    ACTION_CHOICES = [
        ("project_created", "Dossier créé"),
        ("budget_updated", "Budget modifié"),
        ("expense_created", "Dépense créée"),
        ("expense_updated", "Dépense modifiée"),
        ("expense_deleted", "Dépense supprimée"),
        ("key_date_created", "Date clé créée"),
        ("key_date_updated", "Date clé modifiée"),
        ("key_date_deleted", "Date clé supprimée"),
        ("action_created", "Action créée"),
        ("action_updated", "Action modifiée"),
        ("action_deleted", "Action supprimée"),
        ("status_updated", "Statut modifié"),
        ("project_deleted", "Dossier supprimé"),
    ]

    project = models.ForeignKey(
        TechnicalProject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="history",
        verbose_name="Dossier",
    )
    project_reference = models.CharField("Référence dossier", max_length=50, blank=True)
    project_name = models.CharField("Nom du dossier", max_length=255, blank=True)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_project_history",
        verbose_name="Utilisateur",
    )
    action = models.CharField("Action", max_length=30, choices=ACTION_CHOICES)
    target_type = models.CharField("Type de cible", max_length=50)
    target_label = models.CharField("Libellé cible", max_length=255, blank=True)
    before = models.JSONField("Avant", default=dict, blank=True)
    after = models.JSONField("Après", default=dict, blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        db_table = "historique_projet_technique"
        ordering = ["-created_at", "-id"]
        verbose_name = "Historique dossier technique"
        verbose_name_plural = "Historiques dossiers techniques"

    def __str__(self):
        project_label = self.project_reference or "Dossier supprimé"
        return f"{project_label} - {self.get_action_display()}"


class TechnicalEmail(models.Model):
    STATUS_CHOICES = [
        ("classified", "Classé"),
        ("pending", "À valider"),
        ("unassigned", "Non classé"),
    ]

    subject = models.CharField("Objet", max_length=255)
    sender = models.CharField("Expéditeur", max_length=255)
    recipients = models.TextField("Destinataires", blank=True)
    cc = models.TextField("Copie", blank=True)
    body = models.TextField("Contenu", blank=True)
    received_at = models.DateTimeField("Reçu le")

    external_id = models.CharField(
        "Identifiant externe",
        max_length=255,
        blank=True,
        null=True,
    )
    thread_id = models.CharField(
        "Identifiant de conversation Gmail",
        max_length=255,
        blank=True,
        default="",
    )

    has_attachments = models.BooleanField("Pièces jointes", default=False)
    project = models.ForeignKey(
        TechnicalProject, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="emails", verbose_name="Dossier associé",
    )
    status = models.CharField(
        "Statut de classement", max_length=20, choices=STATUS_CHOICES, default="unassigned",
    )
    imported_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="imported_technical_emails", verbose_name="Importé par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        db_table = "technical_email"
        ordering = ["-received_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_id", "imported_by"],
                name="unique_email_per_user",
                condition=models.Q(external_id__isnull=False),
            )
        ]

    def __str__(self):
        return self.subject


class TechnicalEmailAttachment(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ("pending", "En attente"),
        ("processing", "Traitement en cours"),
        ("linked", "Document créé"),
        ("skipped", "Ignoré"),
        ("error", "Erreur"),
    ]

    email = models.ForeignKey(TechnicalEmail, related_name="attachments", on_delete=models.CASCADE, verbose_name="Email")
    file = models.FileField("Fichier", upload_to="documents_tech/emails/")
    original_name = models.CharField("Nom d'origine", max_length=255)
    content_type = models.CharField("Type MIME", max_length=150, blank=True)
    size = models.PositiveIntegerField("Taille", default=0)
    extracted_text = models.TextField("Texte extrait", blank=True)
    linked_document = models.ForeignKey(
        "DocumentTechnique", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="source_attachments", verbose_name="Document technique lié",
    )
    processing_status = models.CharField(
        "État du traitement",
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
    )
    processing_error = models.TextField("Erreur de traitement", blank=True)
    processed_at = models.DateTimeField("Traité le", null=True, blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        db_table = "technical_email_attachment"
        ordering = ["id"]

    def __str__(self):
        return self.original_name
