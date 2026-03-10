from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatbotQuery(models.Model):
    QUERY_TYPES = [
        ("invoice", "Facture"),
        ("legal", "Juridique"),
        ("legal_fallback", "Juridique fallback"),
        ("unknown", "Inconnu"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chatbot_queries",
        verbose_name="Utilisateur",
    )
    message = models.TextField("Question")
    response = models.TextField("Réponse")
    query_type = models.CharField(
        "Type de requête",
        max_length=20,
        choices=QUERY_TYPES,
        default="unknown",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Historique chatbot"
        verbose_name_plural = "Historique chatbot"

    def __str__(self):
        return f"{self.user} - {self.query_type} - {self.created_at:%d/%m/%Y %H:%M}"