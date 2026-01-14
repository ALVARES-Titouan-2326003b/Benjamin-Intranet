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
        db_table = 'Utilisateurs'
        managed = False

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})" if self.prenom and self.nom else self.email


class Modele_Relance(models.Model):
    """
    Modèle représentant la table Modele_Relance
    Contient les messages de relance personnalisés pour chaque utilisateur
    Relation 1-1 : Un utilisateur = Un modèle de relance
    """

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
    """
    id = models.TextField(primary_key=True)
    pole = models.TextField()
    relance = models.IntegerField()

    class Meta:
        db_table = 'Temps_Relance'
        managed = False

    def __str__(self):
        return f"Relance tous les {self.relance} jours pour utilisateur {self.id}"

class Activites(models.Model):
    """
    Modèle représentant la table Activites
    Contient les événements/activités liés aux dossiers à afficher dans le calendrier
    """
    id = models.AutoField(primary_key=True)
    dossier = models.TextField()
    type = models.TextField()
    pole = models.TextField()
    date = models.DateTimeField()
    date_type = models.TextField(blank=True, null=True)
    commentaire = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Activites'
        managed = False
        ordering = ['date']

    def __str__(self):
        return f"{self.type} - {self.dossier} ({self.date.strftime('%Y-%m-%d')})"


class OAuthToken(models.Model):
    """
    Stocke les tokens OAuth2 pour l'accès aux boîtes mail des utilisateurs
    """
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='oauth_token'
    )


    provider = models.CharField(max_length=50, default='google')


    email = models.EmailField()


    access_token = models.TextField()
    refresh_token = models.TextField()


    token_expiry = models.DateTimeField()


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oauth_tokens'
        verbose_name = 'Token OAuth'
        verbose_name_plural = 'Tokens OAuth'
        managed = False

    def __str__(self):
        return f"OAuth {self.provider} - {self.user.username} ({self.email})"

    def is_token_expired(self):
        """Vérifie si l'access_token est expiré"""
        from django.utils import timezone
        return timezone.now() >= self.token_expiry