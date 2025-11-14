from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class FicheDePoste(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(help_text="Missions, responsabilités, contexte.")
    competences_clees = models.TextField(
        blank=True,
        help_text="Compétences clés (séparées par des virgules)."
    )
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre

class Candidat(models.Model):
    nom = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    cv_fichier = models.FileField(upload_to="cv/")
    cv_texte = models.TextField(blank=True)  # texte extrait (PDF -> texte)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

class Candidature(models.Model): 
    STATUTS = [
        ("nouvelle", "Nouvelle"),
        ("retenue", "Retenue"),
        ("refus", "Refus"),
    ]
    fiche = models.ForeignKey(FicheDePoste, on_delete=models.CASCADE, related_name="candidatures")
    candidat = models.ForeignKey(Candidat, on_delete=models.CASCADE, related_name="candidatures")
    score = models.FloatField(null=True, blank=True)  # Score 0-100
    explication = models.TextField(blank=True)  # Explication du score
    statut = models.CharField(max_length=20, choices=STATUTS, default="nouvelle")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("fiche", "candidat")]
        ordering = ["-score", "-created_at"]

    def __str__(self):
        return f"{self.candidat} ↔ {self.fiche} ({self.score or '—'})"
