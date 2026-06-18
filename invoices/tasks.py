import logging

from celery import shared_task
from django.utils import timezone

from management.gmail_service import send_message
from management.oauth_utils import get_valid_credentials

from .models import (
    Contact,
    EmailFournisseur,
    Facture,
    FactureHistorique,
    InvoiceReminderSettings,
    RelanceFournisseur,
)

logger = logging.getLogger(__name__)


def _invoice_sender():
    settings = (
        InvoiceReminderSettings.objects.select_related("sender", "sender__oauth_token")
        .filter(pk=1)
        .first()
    )
    sender = settings.sender if settings else None
    if not sender or not sender.is_active:
        raise ValueError("Aucun compte Gmail actif n'est désigné pour les relances de factures.")
    token = getattr(sender, "oauth_token", None)
    if not token or token.provider != "google":
        raise ValueError("Le compte expéditeur des relances n'a pas synchronisé Gmail.")
    try:
        get_valid_credentials(token)
    except Exception as exc:
        raise ValueError(
            "Le jeton Gmail du compte expéditeur est invalide ou ne peut pas être renouvelé."
        ) from exc
    return sender


def _supplier_email(facture):
    contacts = Contact.objects.filter(acteur=facture.fournisseur_id)
    return (
        EmailFournisseur.objects.filter(contact__in=contacts)
        .exclude(email="")
        .values_list("email", flat=True)
        .first()
        or ""
    )


def _format_message(facture, template, days_overdue):
    client_name = str(facture.client) if facture.client_id else "-"
    context = {
        "facture_id": facture.id,
        "montant": facture.montant or 0,
        "echeance": facture.echeance.strftime("%d/%m/%Y") if facture.echeance else "—",
        "jours_retard": days_overdue,
        "jours_apres_echeance": days_overdue,
        # Compatibilité avec les anciens modèles de message.
        "jours_avant_echeance": days_overdue,
        "fournisseur": facture.fournisseur,
        "client": client_name,
    }
    try:
        return template.format(**context)
    except KeyError:
        logger.warning("Variables inconnues dans le modèle de relance pour %s", facture.pk)
        return template


def _record_history(
    facture,
    action,
    details,
    recipient_email="",
    days_overdue=None,
    external_message_id="",
):
    return FactureHistorique.objects.create(
        facture=facture,
        action=action,
        details=details,
        recipient_email=recipient_email,
        days_overdue=days_overdue,
        external_message_id=external_message_id,
    )


def send_invoice_reminder(facture, to_email, message_text, days_overdue, sender=None):
    sender = sender or _invoice_sender()
    subject = f"Relance facture {facture.id} - {days_overdue} jour(s) de retard"
    body = _format_message(facture, message_text, days_overdue)

    try:
        result = send_message(
            user=sender,
            to_email=to_email,
            subject=subject,
            body=body,
        )
        _record_history(
            facture,
            "reminder_sent",
            f"Relance Gmail envoyée à {to_email} à J+{days_overdue}",
            recipient_email=to_email,
            days_overdue=days_overdue,
            external_message_id=result.get("message_id", ""),
        )
        return result
    except Exception as exc:
        logger.exception("Erreur d'envoi de la relance pour %s", facture.pk)
        return {"success": False, "message": str(exc)}


def _last_successful_reminder_delay(facture):
    return (
        FactureHistorique.objects.filter(
        facture=facture,
        action="reminder_sent",
        days_overdue__isnull=False,
        )
        .order_by("-days_overdue", "-created_at")
        .values_list("days_overdue", flat=True)
        .first()
    )


@shared_task
def check_and_send_invoice_reminders(delai_relance=None):
    if delai_relance is not None:
        if delai_relance < 1:
            return {"success": False, "message": "Le délai doit être supérieur ou égal à 1."}
        updated = RelanceFournisseur.objects.all().update(temps=delai_relance)
        if not updated:
            return {
                "success": False,
                "message": "Aucune configuration trouvée dans RelanceFournisseur",
            }

    relance_config = RelanceFournisseur.objects.first()
    if not relance_config or not relance_config.temps:
        return {"success": False, "message": "Aucune configuration de relance disponible."}
    if not relance_config.message:
        return {"success": False, "message": "Le modèle de relance est vide."}

    interval = relance_config.temps
    try:
        sender = _invoice_sender()
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    today = timezone.localdate()
    invoices = (
        Facture.objects.filter(
            statut__in=["received", "ongoing"],
            echeance__date__lt=today,
        )
        .select_related("client", "fournisseur")
        .order_by("echeance", "id")
    )

    sent = 0
    processed = 0
    errors = 0
    skipped = 0

    for facture in invoices:
        processed += 1
        days_overdue = (today - facture.echeance.date()).days
        last_delay = _last_successful_reminder_delay(facture)
        if last_delay is None and days_overdue < interval:
            continue
        if last_delay is not None and days_overdue < last_delay + interval:
            skipped += 1
            continue

        recipient = _supplier_email(facture)
        if not recipient:
            _record_history(
                facture,
                "reminder_skipped",
                f"Relance ignorée à J+{days_overdue}: aucun e-mail fournisseur",
                days_overdue=days_overdue,
            )
            skipped += 1
            continue

        result = send_invoice_reminder(
            facture=facture,
            to_email=recipient,
            message_text=relance_config.message,
            days_overdue=days_overdue,
            sender=sender,
        )
        if result.get("success"):
            sent += 1
        else:
            _record_history(
                facture,
                "reminder_error",
                result.get("message", "Erreur Gmail inconnue"),
                recipient_email=recipient,
                days_overdue=days_overdue,
            )
            errors += 1

    return {
        "success": True,
        "factures_traitees": processed,
        "relances_envoyees": sent,
        "relances_ignorees": skipped,
        "erreurs": errors,
        "delai_applique": interval,
        "sender": sender.email,
    }
