from django.db import models
from django.contrib.auth.models import User


class Fournisseur(models.Model):
    """
    Correspond à un fournisseur

    Attributes:
        id (str): Identifiant du fournisseur
        nom (str): Nom du fournisseur
        contact (str): Contact du fournisseur
    """
    id = models.CharField(primary_key=True, max_length=255)
    nom = models.CharField(max_length=255, null=True, blank=True)
    contact = models.CharField(max_length=255)
    class Meta:
        managed = False
        db_table = '"Fournisseur"'

    def __str__(self):
        return self.nom or self.id


class Entreprise(models.Model):
    """
    Modèle représentant la table Entreprise

    Attributes:
        id (str): Identifiant de l'entreprise
        nom (str): Nom de l'entreprise
    """
    id = models.CharField(primary_key=True, max_length=255)
    nom = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"Entreprise"'

    def __str__(self):
        return self.nom or self.id

class Facture(models.Model):
    """
    Modèle représentant la table Factures.

    Attributes:
        id (str): ID unique format "FAC-XXXXXXXX"
        pole (str): Pôle associé à la facture
        dossier (str): Référence dossier
        fournisseur (str): Nom du fournisseur
        client (ForeignKey): Entreprise
        montant (float): Montant de la facture
        statut (str): Statut ENUM (Recue, En cours, Payée, Refusée, Archivée, En retard)
        echeance (datetime): Date limite de paiement
        titre (str): Titre de la facture
        collaborateur (ForeignKey): Utilisateur assigné
    """
    id = models.CharField(primary_key=True, max_length=255)
    pole = models.CharField(max_length=50)
    dossier = models.CharField(max_length=255)
    fournisseur = models.CharField(max_length=255)
    client = models.ForeignKey(Entreprise, on_delete=models.DO_NOTHING, db_column='client')
    montant = models.FloatField(null=True)
    statut = models.CharField(max_length=50)
    echeance = models.DateTimeField(null=True, blank=True)
    titre = models.CharField(max_length=255, null=True, blank=True)
    collaborateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='collaborateur_id', related_name='factures')

    class Meta:
        managed = False
        db_table = '"Factures"'
        ordering = ['-echeance']

    def __str__(self):
        return f"{self.fournisseur} — {self.montant}€ — {self.statut}"

class Collaborateur(models.Model):
    id = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, db_column='id')

    class Meta:
        managed = False
        db_table = '"Collaborateurs"'

class Justificatif(models.Model):
    facture = models.OneToOneField(Facture, on_delete=models.CASCADE, primary_key=True, db_column='facture')

    class Meta:
        managed = False
        db_table = '"Justificatifs"'


class PieceJointe(models.Model):
    """
    Pièces jointes des factures (stockage local Django).

    Attributes:
        facture (ForeignKey): Facture associée
        fichier (FileField): PDF de la facture
        uploaded_at (datetime): Date d'upload
    """
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE)
    fichier = models.FileField(upload_to='factures/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pieces_upload_local'  # table locale

class Client(models.Model):
    """
    Modèle représentant la table Client.

    Attributes:
        id (str): ID unique
    """
    id = models.CharField(primary_key=True, max_length=255)

    class Meta:
        managed = False
        db_table = '"Client"'

    def __str__(self):
        return self.id

class Dossier(models.Model):
    """
    Modèle représentant la table Dossier.

    Attributes:
        reference (str): ID unique format "DOS-XXXXXXXX"
    """
    reference = models.CharField(primary_key=True, max_length=255, db_column='reference')

    class Meta:
        managed = False
        db_table = '"Dossier"'


class Utilisateur(models.Model):
    id = models.TextField(primary_key=True)
    mdp = models.TextField()
    email = models.TextField()
    nom = models.TextField(blank=True, null=True)
    prenom = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Utilisateurs'
        managed = False

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})" if self.prenom and self.nom else self.email


class Modele_Relance(models.Model):
    utilisateur = models.TextField(primary_key=True)
    metier = models.TextField()
    pole = models.TextField()
    message = models.TextField(blank=True, null=True)
    objet = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Modele_Relance'
        managed = False

    def __str__(self):
        return f"Modèle relance pour utilisateur {self.utilisateur}"


class Temps_Relance(models.Model):
    """
    Modèle représentant la table Temps_Relance
    Contient le nombre de jours entre chaque relance pour chaque utilisateur

    Attributes:
        id (str): Identifiant du temps de relance
        pole (str): Nom du pole
        relance (int): Nombre de jour pour la relance
    """
    id = models.TextField(primary_key=True)
    pole = models.TextField()
    relance = models.IntegerField()

    class Meta:
        db_table = 'Temps_Relance'
        managed = False

    def __str__(self):
        return f"Relance tous les {self.relance} jours pour utilisateur {self.id}"