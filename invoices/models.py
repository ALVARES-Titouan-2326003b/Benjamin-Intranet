from django.db import models
from django.contrib.auth.models import User


class Fournisseur(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    nom = models.CharField(max_length=255, null=True, blank=True)
    contact = models.CharField(max_length=255)
    class Meta:
        db_table = '"Fournisseur"'

    def __str__(self):
        return self.nom or self.id


class Entreprise(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    nom = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
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
    collaborateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='collaborateur_id', related_name='factures')

    class Meta:
        db_table = '"Facture"'
        ordering = ['-echeance']

    def __str__(self):
        return f"{self.fournisseur} — {self.montant}€ — {self.statut}"


class PieceJointe(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE)
    fichier = models.FileField(upload_to='factures/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pieces_upload_local'  # table locale

class Client(models.Model):
    id = models.CharField(primary_key=True, max_length=255)

    class Meta:
        db_table = '"Client"'

    def __str__(self):
        return self.id