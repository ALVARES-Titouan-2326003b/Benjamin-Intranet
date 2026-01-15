from django.db import models
from tmp3 import Contact, Dossier
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
    email = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'email_client'


class TelClient(models.Model):
    pk = models.CompositePrimaryKey('contact', 'tel')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    tel = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'tel_client'


class GeneralModeleRelance(models.Model):
    metier = models.OneToOneField(Metier, on_delete=models.CASCADE, db_column='metier', primary_key=True)
    message = models.TextField()

    class Meta:
        db_table = 'general_modele_relance'


class GeneralTempsRelance(models.Model):
    id = models.TextField(primary_key=True)
    temps = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'general_temps_relance'

    def __str__(self):
        return f"Relance tous les {self.relance} jours"


class TypeActivite(models.Model):
    type = models.TextField(primary_key=True)

    class Meta:
        db_table = 'type_activite'


class Activite(models.Model):
    TYPES = [
        ("echeance", "Échéance"),
        ("date", "Date")
    ]

    id = models.TextField(primary_key=True)
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, db_column='dossier')
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
        managed = False

    def __str__(self):
        return f"OAuth {self.provider} - {self.user.username} ({self.email})"

    def is_token_expired(self):
        """Vérifie si l'access_token est expiré"""
        from django.utils import timezone
        return timezone.now() >= self.token_expiry