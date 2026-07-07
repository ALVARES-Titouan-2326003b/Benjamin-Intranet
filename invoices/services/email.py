from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.urls import reverse


FINANCE_NOTIFICATION_GROUPS = ["POLE_FINANCIER", "CEO"]


def get_internal_recipients(pole_name=None):
    """
    Récupère les emails des utilisateurs du groupe correspondant au pôle.
    """
    mapping = {
        "Technique": "POLE_TECHNIQUE",
        "Administratif": "POLE_ADMINISTRATIF",
        "Promotion": "POLE_PROMOTION",
        "Développement": "POLE_DEVELOPPEMENT",
        "Developpement": "POLE_DEVELOPPEMENT",
        "Investissement": "POLE_INVESTISSEMENT",
        "Comptabilite et Finance": "POLE_FINANCIER",
    }
    target_group = mapping.get(pole_name, "POLE_FINANCIER")

    User = get_user_model()
    group_users = User.objects.filter(groups__name=target_group).exclude(email="")
    return list({user.email for user in group_users})


def get_finance_notification_recipients():
    """
    Récupère les destinataires des notifications finance :
    membres du pôle financier + CEO.
    """
    User = get_user_model()
    users = (
        User.objects.filter(groups__name__in=FINANCE_NOTIFICATION_GROUPS, is_active=True)
        .exclude(email="")
        .distinct()
        .order_by("email")
    )
    return list(dict.fromkeys(user.email for user in users))


def _invoice_link(facture):
    relative_link = reverse("invoices:detail", args=[facture.pk])
    return f"{settings.SITE_URL}{relative_link}"


def _invoice_details(facture):
    demandeur = "-"
    if facture.demandeur_id:
        demandeur = facture.demandeur.get_full_name() or facture.demandeur.username

    return (
        f"Fournisseur : {facture.fournisseur or '-'}\n"
        f"Numéro de facture : {facture.numero_facture or '-'}\n"
        f"Société : {facture.societe or '-'}\n"
        f"Dossier / affaire : {facture.affaire or '-'}\n"
        f"Montant TTC : {facture.montant if facture.montant is not None else '-'} €\n"
        f"Échéance : {facture.echeance.strftime('%d/%m/%Y') if facture.echeance else '-'}\n"
        f"Demandeur : {demandeur}\n"
        f"Service / pôle : {facture.get_service_display() if facture.service else '-'}\n"
        f"Priorité : {facture.get_priorite_display() if facture.priorite else '-'}\n"
        f"Lien intranet : {_invoice_link(facture)}"
    )


def _send_finance_email(subject, body):
    recipients = get_finance_notification_recipients()
    if not recipients:
        return False

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        email.send()
        return True
    except Exception as exc:
        print(f"Erreur lors de l'envoi de la notification finance : {exc}")
        return False


def send_invoice_submission_email(facture):
    """
    Notifie le pôle financier et les CEO lorsqu'une facture est transmise.
    """
    subject = f"Nouvelle facture transmise : {facture.numero_facture or facture.id}"
    body = (
        "Bonjour,\n\n"
        "Une nouvelle facture a été transmise dans l'intranet.\n\n"
        f"{_invoice_details(facture)}\n\n"
        "Cordialement,\n"
        "L'intranet Benjamin Immobilier"
    )
    return _send_finance_email(subject, body)


def send_invoice_status_email(facture, old_status, new_status):
    """
    Notifie le pôle financier et les CEO lors du changement de statut.
    """
    subject = f"Mise à jour facture {facture.numero_facture or facture.id} : statut modifié"
    body = (
        "Bonjour,\n\n"
        f"Le statut de la facture {facture.numero_facture or facture.id} a changé.\n\n"
        f"Ancien statut : {old_status}\n"
        f"Nouveau statut : {new_status}\n\n"
        f"{_invoice_details(facture)}\n\n"
        "Cordialement,\n"
        "L'intranet Benjamin Immobilier"
    )
    return _send_finance_email(subject, body)
