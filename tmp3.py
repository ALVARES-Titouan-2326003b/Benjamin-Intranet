from django.db import models
from django.contrib.auth import get_user_model
Utilisateur = get_user_model()


class GeneralModeleRelanceFournisseur(models.Model):
    id = models.TextField(primary_key=True)
    message = models.TextField()

    class Meta:
        db_table = 'general_modele_relance_fournisseur'



class Dossier(models.Model):
    TYPES = [
        ("client", "Client"),
        ("juridique", "Juridique")
    ]

    reference = models.TextField(primary_key=True)
    type = models.TextField(choices=TYPES, default="client")
    frais_eng = models.FloatField(blank=True, null=True)
    fais_payes = models.FloatField(blank=True, null=True)
    frais_rest = models.FloatField(blank=True, null=True)
    total_estim = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'dossier'


class ActeurExterne(models.Model):
    id = models.TextField(primary_key=True)

    class Meta:
        db_table = 'acteur_externe'


class Contact(models.Model):
    id = models.TextField(primary_key=True)
    acteur = models.ForeignKey(ActeurExterne, on_delete=models.CASCADE, db_column='id')
    nom = models.TextField(blank=True, null=True)
    prenom = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'contact'


class Client(models.Model):
    id = models.OneToOneField(ActeurExterne, on_delete=models.CASCADE, db_column='id', primary_key=True)

    class Meta:
        db_table = 'client'

    def __str__(self):
        return self.id


class ClientDossier(models.Model):
    pk = models.CompositePrimaryKey('dossier', 'client')
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, db_column='dossier')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, db_column='client')

    class Meta:
        db_table = 'client_dossier'


class Entreprise(models.Model):
    id = models.OneToOneField(Client, on_delete=models.CASCADE, db_column='id', primary_key=True)
    nom = models.TextField()

    class Meta:
        db_table = 'entreprise'

    def __str__(self):
        return self.nom or self.id


class Particulier(models.Model):
    id = models.OneToOneField(Client, on_delete=models.CASCADE, db_column='id', primary_key=True)
    nom = models.TextField()
    prenom = models.TextField()

    class Meta:
        db_table = 'particulier'

    def __str__(self):
        return f"{upper(self.nom)} {self.prenom}" or self.id


class EmailFournisseur(models.Model):
    pk = models.CompositePrimaryKey('contact', 'email')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    email = models.TextField()

    class Meta:
        db_table = 'email_fournisseur'


class TelFournisseur(models.Model):
    pk = models.CompositePrimaryKey('contact', 'tel')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact')
    tel = models.TextField()

    class Meta:
        db_table = 'tel_fournisseur'


class Fournisseur(models.Model):
    id = models.OneToOneField(ActeurExterne, on_delete=models.CASCADE, db_column='id', primary_key=True)
    nom = models.TextField()

    class Meta:
        db_table = 'fournisseur'

    def __str__(self):
        return self.nom or self.id


class Facture(models.Model):
    STATUS = [
        ("ongoing", "En cours"),
        ("received", "Reçue"),
        ("denied", "Refusée"),
        ("paid", "Payée"),
        ("archived", "Archivée"),
    ]

    id = models.CharField(primary_key=True)
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, db_column='dossier')
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.DO_NOTHING, db_column='fournisseur')
    client = models.ForeignKey(Entreprise, on_delete=models.DO_NOTHING, db_column='client')
    montant = models.FloatField(null=True)
    statut = models.TextField(choices=STATUS, default="ongoing")
    echeance = models.DateTimeField(null=True, blank=True)
    titre = models.CharField(max_length=255, null=True, blank=True)
    collaborateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
                                      db_column='collaborateur_id', related_name='factures')

    def __str__(self):
        return f"{self.fournisseur} — {self.montant}€ — {self.statut}"

    class Meta:
        db_table = 'facture'


class PieceJointe(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, db_column="facture")
    fichier = models.FileField(upload_to='factures/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pieces_upload_local'  # table locale