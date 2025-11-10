from django.db import models
from django.contrib.auth.models import User


class Fournisseur(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    nom = models.CharField(max_length=255, null=True, blank=True)
    contact = models.CharField(max_length=255)
    class Meta:
        managed = False
        db_table = '"Fournisseur"'

    def __str__(self):
        return self.nom or self.id


class Entreprise(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    nom = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"Entreprise"'

    def __str__(self):
        return self.nom or self.id

class Facture(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    pole = models.CharField(max_length=50)
    dossier = models.CharField(max_length=255)
    fournisseur = models.CharField(max_length=255)
    client = models.ForeignKey(Entreprise, on_delete=models.DO_NOTHING, db_column='client')
    montant = models.FloatField(null=True)
    statut = models.CharField(max_length=50)
    echeance = models.DateTimeField(null=True, blank=True)
    titre = models.CharField(max_length=255, null=True, blank=True)

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
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE)
    fichier = models.FileField(upload_to='factures/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pieces_upload_local'  # table locale

class Client(models.Model):
    id = models.CharField(primary_key=True, max_length=255)

    class Meta:
        managed = False
        db_table = '"Client"'

    def __str__(self):
        return self.id

class Dossier(models.Model):
    reference = models.CharField(primary_key=True, max_length=255, db_column='reference')

    class Meta:
        managed = False
        db_table = '"Dossier"'
