from django.db import models
from tmp2 import Metier, Pole
from django.contrib.auth import get_user_model
Utilisateur = get_user_model()


class ModeleRelance(models.Model):
    pk = models.CompositePrimaryKey('utilisateur', 'metier')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, db_column='utilisateur')
    metier = models.ForeignKey(Metier, on_delete=models.CASCADE, db_column='metier')
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'modele_relance'


class ModeleRelanceFournisseur(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, db_column='utilisateur', primary_key=True)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'modele_relance_fournisseur'


class TempsRelance(models.Model):
    id = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, db_column='id', primary_key=True)
    temps = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'temps_relance'