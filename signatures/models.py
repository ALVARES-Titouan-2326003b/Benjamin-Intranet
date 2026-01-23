import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_signature_token():
    """Génère un token unique pour les demandes de signature."""
    return uuid.uuid4().hex


class SignatureUser(models.Model):
    """
    Signature scannée d'un utilisateur (CEO, etc.).

    Attributes:
        user (OneToOneField): Utilisateur
        image (ImageFieldFile): Fichier image de la signature
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signature_profile",
    )
    image = models.ImageField(upload_to="signatures/")

    class Meta:
        db_table = 'signature_utilisateur'

    def __str__(self):
        return f"Signature de {self.user.get_username()}"


class Tampon(models.Model):
    """
    Tampon officiel de l'entreprise.

    Attributes:
        nom (str): Nom du tampon
        image (ImageFieldFile): Fichier image du tampon
    """
    nom = models.CharField(max_length=200, default="Tampon officiel")
    image = models.ImageField(upload_to="tampons/")

    class Meta:
        db_table = 'tampon'

    def __str__(self):
        return self.nom


class Document(models.Model):
    """
    Document PDF à signer.

    Attributes:
        titre (str): Titre du document
        fichier (FileField): PDF original
        fichier_signe (FileField): PDF signé (null si non signé)
        date_upload (datetime): Date d'ajout
    """
    titre = models.CharField(max_length=255)
    fichier = models.FileField(upload_to="documents/originaux/")
    fichier_signe = models.FileField(
        upload_to="documents/signes/", null=True, blank=True
    )
    date_upload = models.DateTimeField(auto_now_add=True)

    # anciennes positions (peuvent servir encore dans certains écrans)
    stamp_x = models.FloatField(null=True, blank=True)
    stamp_y = models.FloatField(null=True, blank=True)
    sig_x = models.FloatField(null=True, blank=True)
    sig_y = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'document'

    def __str__(self):
        return self.titre


class HistoriqueSignature(models.Model):
    """
    Historique des états d'un document dans le workflow de signature.

    Attributes:
        document (Document): Document à signer
        statut (str): Etat du document
        date_action (datetime): Date et heure de la modification du statut
        commentaire (str): Description détaillée
    """
    STATUTS = [
        ("upload", "Document ajouté"),
        ("en_attente", "En attente de signature"),
        ("signe", "Signé"),
        ("refuse", "Refusé"),
        ("erreur", "Erreur"),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="historique",
    )
    statut = models.CharField(max_length=30, choices=STATUTS)
    date_action = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)

    class Meta:
        db_table = 'historique_signature'

    def __str__(self):
        return f"{self.document} - {self.statut}"


class SignatureRequest(models.Model):
    """
    Modèle correspondant à une demande de signature

    Attributes:
        document (Document): Document à signer
        requested_by (User): Utilisateur qui a créé la demande
        approver (User): Utilisateur qui reçoie la demande
        pos_x_pct (float): Position x en pourcentage
        pos_y_pct (float): Position y en pourcentage
        statut (str): Statut de la demande
        token (str): Jeton de la demande
        created_at (datetime): Date et heure de création de la demande
        decided_at (datetime): Date et heure de la signature
        commentaire_ceo (str): Commentaire écrit par le CEO
    """
    STATUTS = [
        ("pending", "En attente"),
        ("approved", "Approuvée"),
        ("refused", "Refusée"),
        ("expired", "Expirée"),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="demandes_signature",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signatures_demandes_emises",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signatures_demandes_a_valider",
    )

    # position choisie par le collaborateur (en %)
    pos_x_pct = models.FloatField()
    pos_y_pct = models.FloatField()

    statut = models.CharField(max_length=20, choices=STATUTS, default="pending")

    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_signature_token,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    commentaire_ceo = models.TextField(blank=True)

    def marquer_approuvee(self, commentaire=""):
        """
        Approuve la demande

        Args:
            commentaire (str): Commentaire du CEO
        """
        self.statut = "approved"
        self.decided_at = timezone.now()
        self.commentaire_ceo = commentaire
        self.save()

    def marquer_refusee(self, commentaire=""):
        """
        Refuse la demande

        Args:
            commentaire (str): Commentaire du CEO
        """
        self.statut = "refused"
        self.decided_at = timezone.now()
        self.commentaire_ceo = commentaire
        self.save()

    class Meta:
        db_table = 'demande_signature'

    def __str__(self):
        return f"Demande pour {self.document} ({self.get_statut_display()})"
