from django.core.mail import EmailMessage
from django.conf import settings


def _normaliser_destinataires(destinataires):
    if isinstance(destinataires, str):
        valeurs = [destinataires]
    else:
        valeurs = list(destinataires or [])

    emails = []
    deja_vus = set()
    for email in valeurs:
        email = (email or "").strip()
        cle = email.lower()
        if email and cle not in deja_vus:
            deja_vus.add(cle)
            emails.append(email)
    return emails


def envoyer_demande_signature(signataire_email, lien_approbation: str, document):
    """
    Envoie l'email de demande de signature a un ou plusieurs destinataires.
    """
    destinataires = _normaliser_destinataires(signataire_email)
    if not destinataires:
        raise ValueError("Aucun destinataire de signature configure.")

    titre_doc = document.titre or document.fichier.name

    sujet = f"[Signature requise] {titre_doc}"
    corps = (
        f"Bonjour,\n\n"
        f"Un document est en attente d'approbation pour signature.\n\n"
        f"Titre : {titre_doc}\n"
        f"Consulter et approuver ou refuser ici : {lien_approbation}\n\n"
        f"Bien cordialement,\n"
        f"L'intranet Benjamin Immobilier"
    )

    email = EmailMessage(
        subject=sujet,
        body=corps,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinataires,
    )

    email.send()
    return destinataires
