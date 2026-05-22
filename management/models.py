"""
Modèles pour la partie administrative - Gestion des relances
"""
from django.db import models
from invoices.models import Contact
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
        return f"Relance tous les {self.temps} jours"


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


class AdministrativeProject(models.Model):
    PROJECT_TYPES = [
        ("client", "Client"),
        ("juridique", "Juridique"),
        ("interne", "Interne"),
    ]

    reference = models.CharField("Référence projet", max_length=50, unique=True)
    name = models.CharField("Nom du projet", max_length=255)
    type = models.CharField(max_length=20, choices=PROJECT_TYPES, default="client")
    total_estimated = models.DecimalField("Budget estimé", max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_projects_created",
    )
    updated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_projects_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "administrative_project"
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} - {self.name}"


class Activite(models.Model):
    """
    Modèle représentant la table Activites
    Contient les événements/activités liés aux dossiers à afficher dans le calendrier
    """

    TYPES = [
        ("echeance", "Échéance"),
        ("date", "Date")
    ]

    STATUTS = [
        ("todo", "À faire"),
        ("in_progress", "En cours"),
        ("done", "Terminé"),
        ("cancelled", "Annulé"),
    ]

    PRIORITES = [
        ("low", "Basse"),
        ("normal", "Normale"),
        ("high", "Haute"),
        ("urgent", "Urgente"),
    ]

    id = models.TextField(primary_key=True)
    titre = models.CharField(max_length=255, blank=True)
    dossier = models.ForeignKey(AdministrativeProject, on_delete=models.CASCADE, db_column='dossier')
    type = models.ForeignKey(TypeActivite, on_delete=models.CASCADE, db_column='type')
    date = models.DateTimeField(blank=True, null=True)
    date_type = models.TextField(choices=TYPES, default="echeance")
    commentaire = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default="todo")
    priorite = models.CharField(max_length=20, choices=PRIORITES, default="normal")
    responsable = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activites_assignees",
    )
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activites_creees",
    )
    updated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activites_modifiees",
    )
    client = models.CharField(max_length=255, blank=True)
    contact_externe = models.CharField(max_length=255, blank=True)
    outlook_event_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activite'
        ordering = ['date']

    def __str__(self):
        date_label = self.date.strftime('%Y-%m-%d') if self.date else "sans date"
        return f"{self.titre or self.type} - {self.dossier} ({date_label})"


class HistoriqueRappelActivite(models.Model):
    CANAUX = [
        ("email", "E-mail"),
        ("interne", "Notification interne"),
    ]

    STATUTS = [
        ("sent", "Envoyé"),
        ("failed", "Échec"),
    ]

    activite = models.ForeignKey(
        Activite,
        on_delete=models.CASCADE,
        related_name="rappels",
    )
    canal = models.CharField(max_length=20, choices=CANAUX)
    destinataire = models.CharField(max_length=255, blank=True)
    jours_avant_echeance = models.IntegerField()
    statut = models.CharField(max_length=20, choices=STATUTS)
    erreur = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historique_rappel_activite"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["activite", "canal", "destinataire", "jours_avant_echeance"],
                name="uniq_rappel_activite_canal_dest_jour",
            )
        ]

    def __str__(self):
        return f"{self.activite_id} J-{self.jours_avant_echeance} {self.canal}"


class NotificationInterne(models.Model):
    user = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="notifications_internes",
    )
    activite = models.ForeignKey(
        Activite,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    titre = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification_interne"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.titre}"


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


    provider = models.CharField(max_length=50, default='microsoft')


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
