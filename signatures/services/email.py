from django.core.mail import EmailMessage
from django.conf import settings


def envoyer_demande_signature(ceo_email: str, lien_approbation: str, document):
    """
    Envoie l'email de demande de signature au CEO.
    """
    titre_doc = document.titre or document.fichier.name

    sujet = f"[Signature requise] Document #{document.pk} - {titre_doc}"
    corps = (
        f"Bonjour,\n\n"
        f"Un document est en attente de votre approbation pour signature.\n\n"
        f"Titre : {titre_doc}\n"
        f"Consulter et approuver ou refuser ici : {lien_approbation}\n\n"
        f"Bien cordialement,\n"
        f"L'intranet Benjamin Immobilier"
    )

    email = EmailMessage(
        subject=sujet,
        body=corps,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[ceo_email],
    )

    email.send()
