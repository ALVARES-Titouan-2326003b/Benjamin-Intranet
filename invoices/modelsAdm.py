"""
Modèles pour la partie administrative - Gestion des relances
"""
from django.db import models


class Utilisateur(models.Model):
    """
    Modèle représentant la table Utilisateurs
    Contient les informations des clients/destinataires

    Attributes:
        email (str): Email de l'utilisateur
        nom (str): Nom de l'utilisateur
        prenom (str): Prenom de l'utilisateur
        mdp (str): Mot de passe de l'utilisateur
    """
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    mdp = models.CharField(max_length=255)

    class Meta:
        db_table = 'Utilisateurs'  # Nom exact de la table existante
        managed = False  # Django ne gère pas cette table (déjà créée en BD)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"


class Relance(models.Model):
    """
    Modèle représentant la table Relance
    Contient les informations de relance pour chaque utilisateur
    Relation 1-1 : Un utilisateur = Une relance

    Attributes:
        utilisateur (int): Identifiant de l'utilisateur
        entreprise (str): Entreprise du contact
        client (str): Client
        date (datetime): Date de la relance
        dossier (str): Dossier associé à la relance
        statut (str): Statut de la relance
        commentaire (str): Commentaire
    """
    utilisateur = models.IntegerField()  # ID de l'utilisateur (Foreign Key manuelle)
    entreprise = models.CharField(max_length=255)
    client = models.CharField(max_length=255)
    date = models.DateTimeField()
    dossier = models.CharField(max_length=255)
    statut = models.CharField(max_length=50)
    commentaire = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Relance'  # Nom exact de la table existante
        managed = False  # Django ne gère pas cette table (déjà créée en BD)

    def __str__(self):
        return f"Relance {self.dossier} - {self.statut}"