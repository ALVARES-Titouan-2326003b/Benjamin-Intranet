from django.db import models
from django.utils import timezone
from technique.models import TechnicalProject
from django.contrib.auth import get_user_model
Utilisateur = get_user_model()


class RelanceFournisseur(models.Model):
    id = models.TextField(primary_key=True)
    message = models.TextField()
    temps = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'relance_fournisseur'


class ActeurExterne(models.Model):
    id = models.TextField(primary_key=True)

    class Meta:
        db_table = 'acteur_externe'


class Contact(models.Model):
    id = models.TextField(primary_key=True)
    acteur = models.ForeignKey(ActeurExterne, on_delete=models.CASCADE, db_column='acteur')
    nom = models.TextField(blank=True, null=True)
    prenom = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'contact'


class Client(models.Model):
    id = models.OneToOneField(ActeurExterne, on_delete=models.CASCADE, db_column='id', primary_key=True)

    class Meta:
        db_table = 'client'

    def __str__(self):
        # Essayer d'abord comme entreprise
        try:
            entreprise = self.entreprise
            return entreprise.nom or str(self.id_id)
        except Entreprise.DoesNotExist:
            pass

        # Essayer comme particulier
        try:
            particulier = self.particulier
            return f"{particulier.nom.upper()} {particulier.prenom}"
        except Particulier.DoesNotExist:
            pass

        # Fallback sur l'ID
        return str(self.id_id)


class ClientDossier(models.Model):
    client = models.ForeignKey("invoices.Client", on_delete=models.CASCADE)
    dossier = models.ForeignKey("technique.TechnicalProject", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["client", "dossier"], name="uniq_client_dossier")
        ]

class Entreprise(models.Model):
    id = models.OneToOneField(Client, on_delete=models.CASCADE, db_column='id', primary_key=True)
    nom = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'entreprise'

    def __str__(self):
        return self.nom or str(self.id_id)


class Particulier(models.Model):
    id = models.OneToOneField(Client, on_delete=models.CASCADE, db_column='id', primary_key=True)
    nom = models.TextField()
    prenom = models.TextField()

    class Meta:
        db_table = 'particulier'

    def __str__(self):
        return f"{self.nom.upper()} {self.prenom}" or self.id


class EmailFournisseur(models.Model):
    pk = models.CompositePrimaryKey('contact', 'email')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    email = models.TextField()

    class Meta:
        db_table = 'email_fournisseur'


class TelFournisseur(models.Model):
    pk = models.CompositePrimaryKey('contact', 'tel')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    tel = models.TextField()

    class Meta:
        db_table = 'tel_fournisseur'


class Fournisseur(models.Model):
    id = models.OneToOneField(ActeurExterne, on_delete=models.CASCADE, db_column='id', primary_key=True)
    nom = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'fournisseur'

    def __str__(self):
        return self.nom or str(self.id_id)


class Facture(models.Model):
    STATUS = [
        ("ongoing", "En cours"),
        ("received", "Reçue"),
        ("denied", "Refusée"),
        ("paid", "Payée"),
        ("archived", "Archivée"),
    ]
    SERVICE_CHOICES = [
        ("developpement", "Développement"),
        ("administratif", "Administratif"),
        ("technique", "Technique"),
        ("promotion", "Promotion"),
        ("investissement", "Investissement"),
        ("fonciere", "Foncière"),
        ("financier", "Financier"),
    ]
    PRIORITY_CHOICES = [
        ("normal", "Normal"),
        ("urgent", "Urgent"),
        ("critical", "Critique"),
    ]

    id = models.CharField(primary_key=True, max_length=255)
    numero_facture = models.CharField("N° de facture", max_length=100, blank=True, default="")
    societe = models.CharField("Société concernée", max_length=255, blank=True, default="")
    affaire = models.CharField("Affaire concernée", max_length=255, blank=True, default="")
    dossier = models.ForeignKey(TechnicalProject, on_delete=models.CASCADE, db_column='dossier')
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.DO_NOTHING, db_column='fournisseur')
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column='client')
    montant = models.FloatField("Montant TTC (€)", null=True)
    statut = models.TextField(choices=STATUS, default="ongoing")
    service = models.CharField(max_length=100, choices=SERVICE_CHOICES, blank=True, default="")
    date_facture = models.DateField("Date de facture", null=True, blank=True)
    date_soumission = models.DateTimeField("Date de soumission", default=timezone.now)
    echeance = models.DateTimeField("Échéance de paiement", null=True, blank=True)
    priorite = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal")
    commentaire_compta = models.TextField("Commentaire pour la compta", blank=True, default="")
    titre = models.CharField(max_length=255, null=True, blank=True)
    demandeur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
                                  db_column='demandeur_id', related_name='factures_demandees')
    collaborateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
                                      db_column='collaborateur_id', related_name='factures')
    created_by = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
                                   db_column='created_by_id', related_name='factures_created')

    def __str__(self):
        return f"{self.fournisseur} — {self.montant}€ — {self.statut}"

    class Meta:
        db_table = 'facture'


class FactureHistorique(models.Model):
    ACTION_CHOICES = [
        ('status_change', 'Changement de statut'),
        ('reminder_sent', 'Relance envoyée'),
        ('reminder_skipped', 'Relance ignorée'),
        ('reminder_error', 'Erreur de relance'),
        ('user_action', 'Action utilisateur'),
    ]

    facture = models.ForeignKey(
        'Facture', on_delete=models.CASCADE, related_name='historique', verbose_name='Facture'
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    old_status = models.CharField(max_length=50, blank=True, null=True)
    new_status = models.CharField(max_length=50, blank=True, null=True)
    user = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Utilisateur'
    )
    details = models.TextField(blank=True, null=True)
    recipient_email = models.EmailField(blank=True, default="")
    days_overdue = models.PositiveIntegerField(null=True, blank=True)
    external_message_id = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facture_historique'
        ordering = ['-created_at']

    def __str__(self):
        return f"Historique {self.facture_id} [{self.get_action_display()}] {self.created_at:%d/%m/%Y %H:%M}"


class InvoiceReminderSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    sender = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_reminder_settings",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoice_reminder_settings"
        verbose_name = "Configuration des relances de factures"
        verbose_name_plural = "Configuration des relances de factures"

    def save(self, *args, **kwargs):
        self.pk = 1
        if self._state.adding and type(self).objects.filter(pk=1).exists():
            type(self).objects.filter(pk=1).update(
                sender=self.sender,
                updated_at=timezone.now(),
            )
            self._state.adding = False
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Expéditeur Gmail : {self.sender or 'non configuré'}"


class PieceJointe(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, db_column="facture")
    fichier = models.FileField(upload_to='factures/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pieces_upload_local'  # table locale


class ExportCegidRun(models.Model):
    STATUS = [
        ("pending", "En attente"),
        ("success", "Succès"),
        ("error", "Erreur"),
    ]

    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    triggered_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cegid_exports",
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to="exports/cegid/", null=True, blank=True)
    line_count = models.PositiveIntegerField(default=0)
    total_amount = models.FloatField(default=0)
    anomaly_count = models.PositiveIntegerField(default=0)
    warning_summary = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "export_cegid_run"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Export Cegid #{self.pk} - {self.get_status_display()}"
