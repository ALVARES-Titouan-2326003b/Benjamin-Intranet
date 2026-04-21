from django.db import models
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
            return entreprise.nom or self.id
        except Entreprise.DoesNotExist:
            pass

        # Essayer comme particulier
        try:
            particulier = self.particulier
            return f"{particulier.nom.upper()} {particulier.prenom}"
        except Particulier.DoesNotExist:
            pass

        # Fallback sur l'ID
        return self.id


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
        return self.nom or self.id


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
        return self.nom or self.id


class Facture(models.Model):
    STATUS = [
        ("ongoing", "En cours"),
        ("received", "Reçue"),
        ("denied", "Refusée"),
        ("paid", "Payée"),
        ("archived", "Archivée"),
    ]

    id = models.CharField(primary_key=True, max_length=255)
    dossier = models.ForeignKey(TechnicalProject, on_delete=models.CASCADE, db_column='dossier')
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.DO_NOTHING, db_column='fournisseur')
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column='client')
    montant = models.FloatField(null=True)
    statut = models.TextField(choices=STATUS, default="ongoing")
    echeance = models.DateTimeField(null=True, blank=True)
    titre = models.CharField(max_length=255, null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facture_historique'
        ordering = ['-created_at']

    def __str__(self):
        return f"Historique {self.facture_id} [{self.get_action_display()}] {self.created_at:%d/%m/%Y %H:%M}"


class PieceJointe(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, db_column="facture")
    fichier = models.FileField(upload_to='factures/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pieces_upload_local'  # table locale