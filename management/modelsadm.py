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

class Temps_Relance(models.Model):
    """
    Modèle représentant la table Temps_Relance
    Contient le nombre de jours entre chaque relance pour chaque utilisateur
    """
    id = models.TextField(primary_key=True)  # ID utilisateur (FK vers Utilisateurs.id)
    pole = models.TextField()  # Type 'poles' en PostgreSQL (enum)
    relance = models.IntegerField()  # Nombre de jours entre chaque relance

    class Meta:
        db_table = 'Temps_Relance'  # Nom exact de la table existante
        managed = False  # Django ne gère pas cette table (déjà créée en BD)

    def __str__(self):
        return f"Relance tous les {self.relance} jours pour utilisateur {self.id}"

class Activites(models.Model):
    """
    Modèle représentant la table Activites
    Contient les événements/activités liés aux dossiers à afficher dans le calendrier
    """
    id = models.AutoField(primary_key=True)
    dossier = models.TextField()  # Référence au dossier
    type = models.TextField()  # Type d'activité (vente, location, compromis, visite, etc.)
    pole = models.TextField()  # Type 'poles' en PostgreSQL (enum)
    date = models.DateTimeField()  # Date de l'activité
    date_type = models.TextField(blank=True, null=True)  # Type 'date_type' (ignoré pour l'instant)
    commentaire = models.TextField(blank=True, null=True)  # Commentaire optionnel

    class Meta:
        db_table = 'Activites'  # Nom exact de la table existante
        managed = False  # Django ne gère pas cette table (déjà créée en BD)
        ordering = ['date']  # Trier par date par défaut

    def __str__(self):
        return f"{self.type} - {self.dossier} ({self.date.strftime('%Y-%m-%d')})"