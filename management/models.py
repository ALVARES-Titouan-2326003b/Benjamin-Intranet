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


class CategorieDossierAdministratif(models.Model):
    CATEGORIES_OFFICIELLES = [
        "En cours d’acquisition",
        "En cours de vente",
        "Acheté",
        "Vendu",
        "Caduque",
        "Vente annulée",
        "Acquisition annulée",
        "Adjudication",
    ]
    DEFAULT_NOM = CATEGORIES_OFFICIELLES[0]

    nom = models.CharField(max_length=120, unique=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categorie_dossier_administratif"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class ChampPersonnaliseDossier(models.Model):
    FIELD_TYPES = [
        ("text", "Texte"),
        ("date", "Date"),
        ("amount", "Montant"),
        ("number", "Nombre"),
        ("checkbox", "Case à cocher"),
        ("choice", "Liste de choix"),
    ]
    ACTIVITES_METIER = [
        ("", "Toutes les activités"),
        ("marchand_biens", "Marchands de bien"),
        ("promotion_immobiliere", "Promotion immobilière"),
        ("patrimoine", "Patrimoine"),
    ]

    label = models.CharField("Libellé", max_length=120, unique=True)
    activite_metier = models.CharField(
        "Activité métier",
        max_length=40,
        choices=ACTIVITES_METIER,
        blank=True,
        default="",
    )
    field_type = models.CharField("Type de saisie", max_length=20, choices=FIELD_TYPES, default="text")
    choices = models.TextField("Choix possibles", blank=True)
    show_in_detail = models.BooleanField("Afficher dans la fiche dossier", default=True)
    show_in_table = models.BooleanField("Afficher dans le tableau", default=False)
    is_active = models.BooleanField("Actif", default=True)
    sort_order = models.PositiveSmallIntegerField("Ordre", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "champ_personnalise_dossier"
        ordering = ["sort_order", "label"]

    def __str__(self):
        return self.label

    @property
    def choice_list(self):
        return [choice.strip() for choice in self.choices.splitlines() if choice.strip()]


class ValeurChampPersonnaliseDossier(models.Model):
    dossier = models.ForeignKey(
        "technique.TechnicalProject",
        on_delete=models.CASCADE,
        related_name="custom_field_values",
    )
    field = models.ForeignKey(
        ChampPersonnaliseDossier,
        on_delete=models.CASCADE,
        related_name="values",
    )
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "valeur_champ_personnalise_dossier"
        constraints = [
            models.UniqueConstraint(
                fields=["dossier", "field"],
                name="uniq_valeur_champ_personnalise_dossier",
            )
        ]

    def __str__(self):
        return f"{self.dossier_id} - {self.field}"


class AdministrativeProject(models.Model):
    PROJECT_TYPES = [
        ("client", "Client"),
        ("juridique", "Juridique"),
        ("interne", "Interne"),
    ]
    DOSSIER_TYPES = [
        ("vente", "Vente"),
        ("acquisition", "Acquisition"),
    ]
    ACTIVITES_METIER = [
        ("marchand_biens", "Marchands de bien"),
        ("promotion_immobiliere", "Promotion immobilière"),
        ("patrimoine", "Patrimoine"),
    ]
    ETATS = [
        ("promesse", "En cours de promesse"),
        ("vendu", "Vendu"),
        ("achete", "Acheté"),
    ]

    reference = models.CharField("Référence dossier", max_length=50, unique=True)
    name = models.CharField("Nom du dossier", max_length=255)
    type = models.CharField(max_length=20, choices=PROJECT_TYPES, default="client")
    total_estimated = models.DecimalField("Budget estimé", max_digits=12, decimal_places=2, default=0)
    affaire = models.CharField("Affaire", max_length=255, blank=True)
    lot_etage = models.CharField("Lot / étage", max_length=120, blank=True)
    adresse_bien = models.TextField("Adresse du bien", blank=True)
    parcelles = models.TextField(blank=True)
    vendeur = models.CharField(max_length=255, blank=True)
    beneficiaire = models.CharField("Bénéficiaire", max_length=255, blank=True)
    locataire = models.CharField(max_length=255, blank=True)
    type_dossier = models.CharField(max_length=20, choices=DOSSIER_TYPES, default="vente")
    activite_metier = models.CharField(
        max_length=40,
        choices=ACTIVITES_METIER,
        default="marchand_biens",
    )
    etat = models.CharField(max_length=20, choices=ETATS, default="promesse")
    categorie = models.ForeignKey(
        CategorieDossierAdministratif,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dossiers",
    )
    date_promesse = models.DateField(blank=True, null=True)
    premiere_periode = models.CharField("1ère période", max_length=120, blank=True)
    deuxieme_periode = models.CharField("2ème période", max_length=120, blank=True)
    avenant_1 = models.TextField("Avenant 1", blank=True)
    avenant_2 = models.TextField("Avenant 2", blank=True)
    avenant_3 = models.TextField("Avenant 3", blank=True)
    negociation_externe = models.TextField("Négociation externe", blank=True)
    frais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prix = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dg = models.DecimalField("DG", max_digits=12, decimal_places=2, default=0)
    date_dg = models.DateField("Date DG", blank=True, null=True)
    depot_permis = models.DateField("Dépôt permis", blank=True, null=True)
    obtention_permis = models.DateField("Obtention permis", blank=True, null=True)
    diags = models.TextField("Diags", blank=True)
    bornage = models.TextField(blank=True)
    etude_sol_geotechnique = models.TextField("Étude sol / géotechnique", blank=True)
    etude_pollution = models.TextField("Étude pollution", blank=True)
    etude_impact = models.TextField("Étude d’impact", blank=True)
    prorogation = models.TextField(blank=True)
    cs_pret = models.TextField("CS prêt", blank=True)
    date_cs_pret = models.DateField("Date CS prêt", blank=True, null=True)
    date_reiteration = models.DateField("Date de réitération", blank=True, null=True)
    acte = models.TextField(blank=True)
    releves_compte = models.TextField("Relevés de compte", blank=True)
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
        return f"{self.reference} - {self.affaire or self.name}"


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
    DUREES_CRENEAU = [
        (30, "30 min"),
        (60, "1 h"),
        (90, "1 h 30"),
        (120, "2 h"),
    ]

    id = models.TextField(primary_key=True)
    titre = models.CharField(max_length=255, blank=True)
    dossier = models.ForeignKey(
        "technique.TechnicalProject",
        on_delete=models.SET_NULL,
        db_column='dossier',
        null=True,
        blank=True,
    )
    societe = models.ForeignKey(
        "invoices.Societe",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activites",
        verbose_name="Société",
    )
    type = models.ForeignKey(TypeActivite, on_delete=models.CASCADE, db_column='type')
    date = models.DateTimeField(blank=True, null=True)
    duree_minutes = models.PositiveSmallIntegerField("Durée du créneau", choices=DUREES_CRENEAU, default=60)
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

    outlook_event_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activite'
        ordering = ['date']

    def __str__(self):
        date_label = self.date.strftime('%Y-%m-%d') if self.date else "sans date"
        dossier_label = self.dossier or "sans dossier"
        return f"{self.titre or self.type} - {dossier_label} ({date_label})"


class RappelActivite(models.Model):
    """Rappel configuré individuellement pour une activité."""

    TIMING_CHOICES = [
        ("before", "Avant l’échéance"),
        ("after", "Après l’échéance"),
    ]

    activite = models.ForeignKey(
        Activite,
        on_delete=models.CASCADE,
        related_name="rappels_planifies",
    )
    timing = models.CharField(max_length=10, choices=TIMING_CHOICES, default="before")
    days = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rappel_activite"
        ordering = ["timing", "days"]
        constraints = [
            models.UniqueConstraint(
                fields=["activite", "timing", "days"],
                name="uniq_rappel_individuel_activite_timing_days",
            )
        ]

    @property
    def signed_days(self):
        return self.days if self.timing == "before" else -self.days

    @property
    def label(self):
        if self.days == 0:
            return "J0"
        prefix = "J-" if self.timing == "before" else "J+"
        return f"{prefix}{self.days}"

    def __str__(self):
        return f"{self.activite_id} — {self.label}"


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
    date_echeance = models.DateTimeField(blank=True, null=True)
    objet = models.CharField(max_length=255, blank=True)
    contenu = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS)
    erreur = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historique_rappel_activite"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["activite", "canal", "destinataire", "jours_avant_echeance", "date_echeance"],
                name="uniq_rappel_activite_canal_dest_jour",
            )
        ]

    def __str__(self):
        return f"{self.activite_id} J-{self.jours_avant_echeance} {self.canal}"


class RegleRappelActivite(models.Model):
    TIMING_CHOICES = [
        ("before", "Avant l’échéance"),
        ("after", "Après l’échéance"),
    ]

    timing = models.CharField(max_length=10, choices=TIMING_CHOICES, default="before")
    days = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "regle_rappel_activite"
        ordering = ["timing", "days"]
        constraints = [
            models.UniqueConstraint(
                fields=["timing", "days"],
                name="uniq_regle_rappel_activite_timing_days",
            )
        ]

    @property
    def signed_days(self):
        return self.days if self.timing == "before" else -self.days

    @property
    def label(self):
        if self.days == 0:
            return "Le jour même"
        prefix = "J-" if self.timing == "before" else "J+"
        return f"{prefix}{self.days}"

    def __str__(self):
        return self.label


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


class GmailConversation(models.Model):
    STATUS_CHOICES = [
        ("open", "Ouvert"),
        ("reminded", "Relancé"),
        ("replied", "Répondu"),
    ]

    owner = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="gmail_conversations",
    )
    thread_id = models.CharField(max_length=255)
    initial_message_id = models.CharField(max_length=255, blank=True, default="")
    last_message_id = models.CharField(max_length=255, blank=True, default="")
    subject = models.CharField(max_length=500, blank=True, default="")
    recipient = models.EmailField(blank=True, default="")
    preview = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    sent_at = models.DateTimeField(null=True, blank=True)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gmail_conversation"
        ordering = ["-sent_at", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "thread_id"],
                name="uniq_gmail_conversation_owner_thread",
            )
        ]

    def __str__(self):
        return f"{self.subject or '(Sans objet)'} - {self.get_status_display()}"


class GmailConversationEvent(models.Model):
    EVENT_CHOICES = [
        ("synced", "Synchronisation"),
        ("reminder_sent", "Relance envoyée"),
        ("status_changed", "Statut modifié"),
        ("reply_detected", "Réponse détectée"),
        ("note", "Note"),
        ("error", "Erreur"),
    ]

    conversation = models.ForeignKey(
        GmailConversation,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    user = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gmail_conversation_events",
    )
    old_status = models.CharField(max_length=20, blank=True, default="")
    new_status = models.CharField(max_length=20, blank=True, default="")
    note = models.TextField(blank=True, default="")
    external_message_id = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gmail_conversation_event"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.conversation_id} - {self.get_event_type_display()}"
