"""
Modèles pour la partie administrative - Gestion des relances
"""
from django.db import models


class Utilisateur(models.Model):
    """
    Modèle représentant la table Utilisateurs
    Contient les informations des clients/destinataires
    """
    id = models.TextField(primary_key=True)  # ID en text (pas auto-increment)
    mdp = models.TextField()
    email = models.TextField()
    nom = models.TextField(blank=True, null=True)
    prenom = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Utilisateurs'  # Nom exact de la table existante
        managed = False  # Django ne gère pas cette table (déjà créée en BD)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})" if self.prenom and self.nom else self.email


class Modele_Relance(models.Model):
    """
    Modèle représentant la table Modele_Relance
    Contient les messages de relance personnalisés pour chaque utilisateur
    Relation 1-1 : Un utilisateur = Un modèle de relance
    """
    # CORRECTION : Déclarer explicitement utilisateur comme clé primaire
    utilisateur = models.TextField(primary_key=True)  # PK et FK vers Utilisateurs.id
    metier = models.TextField()
    pole = models.TextField()  # Type 'poles' en PostgreSQL (enum)
    message = models.TextField(blank=True, null=True)  # Message de relance personnalisé
    objet = models.TextField(blank=True, null=True)  # Objet/sujet de l'email de relance

    class Meta:
        db_table = 'Modele_Relance'  # Nom exact de la table existante
        managed = False  # Django ne gère pas cette table (déjà créée en BD)

    def __str__(self):
        return f"Modèle relance pour utilisateur {self.utilisateur}"