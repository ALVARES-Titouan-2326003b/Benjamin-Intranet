"""
Modèles pour la partie administrative - Gestion des relances
"""
from django.db import models
from invoices.models import Contact
from technique.models import TechnicalProject
from django.contrib.auth import get_user_model
Utilisateur = get_user_model()


class Pole(models.Model):
    nom = models.TextField(primary_key=True)

    class Meta:
        db_table = 'pole'


class Metier(models.Model):
    nom = models.TextField(primary_key=True)

    class Meta:
        db_table = 'metier'


class EmailClient(models.Model):
    pk = models.CompositePrimaryKey('contact', 'email')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    metier = models.ForeignKey(Metier, on_delete=models.CASCADE, db_column='metier')
    email = models.TextField()

    class Meta:
        db_table = 'email_client'


class TelClient(models.Model):
    pk = models.CompositePrimaryKey('contact', 'tel')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    tel = models.TextField()

    class Meta:
        db_table = 'tel_client'


class DefaultModeleRelance(models.Model):
    metier = models.OneToOneField(Metier, on_delete=models.CASCADE, db_column='metier', primary_key=True)
    message = models.TextField()

    class Meta:
        db_table = 'default_modele_relance'


class DefaultTempsRelance(models.Model):
    id = models.TextField(primary_key=True)
    temps = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'default_temps_relance'

    def __str__(self):
        return f"Relance tous les {self.relance} jours"


class ModeleRelance(models.Model):
    """
    Modèle représentant la table Modele_Relance
    Contient les messages de relance personnalisés pour chaque utilisateur
    Relation 1-1 : Un utilisateur = Un modèle de relance
    """

    pk = models.CompositePrimaryKey('utilisateur', 'metier')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, db_column='utilisateur')
    metier = models.ForeignKey(Metier, on_delete=models.CASCADE, db_column='metier')
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'modele_relance'


class TempsRelance(models.Model):
    """
    Modèle représentant la table Temps_Relance
    Contient le nombre de jours entre chaque relance pour chaque utilisateur
    """

    id = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, db_column='id', primary_key=True)
    temps = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'temps_relance'


class TypeActivite(models.Model):
    type = models.TextField(primary_key=True)

    class Meta:
        db_table = 'type_activite'


class Activite(models.Model):
    """
    Modèle représentant la table Activites
    Contient les événements/activités liés aux dossiers à afficher dans le calendrier
    """

    TYPES = [
        ("echeance", "Échéance"),
        ("date", "Date")
    ]

    id = models.TextField(primary_key=True)
    dossier = models.ForeignKey(TechnicalProject, on_delete=models.CASCADE, db_column='dossier')
    type = models.ForeignKey(TypeActivite, on_delete=models.CASCADE, db_column='type')
    date = models.DateTimeField(blank=True, null=True)
    date_type = models.TextField(choices=TYPES, default="echeance")
    commentaire = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'activite'
        ordering = ['date']

    def __str__(self):
        return f"{self.type} - {self.dossier} ({self.date.strftime('%Y-%m-%d')})"


class OAuthToken(models.Model):
    """
    Stocke les tokens OAuth2 pour l'accès aux boîtes mail des utilisateurs
    """
    user = models.OneToOneField(
        Utilisateur,
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

    def __str__(self):
        return f"OAuth {self.provider} - {self.user.username} ({self.email})"

    def is_token_expired(self):
        """Vérifie si l'access_token est expiré"""
        from django.utils import timezone
        return timezone.now() >= self.token_expiry