import requests
from datetime import timedelta
from management.models import OAuthToken
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from management.oauth_utils import (
    GRAPH_URL,
    get_graph_headers,
    send_email_via_graph_api,
)
from management.gmail_service import (
    get_message as get_gmail_message,
    list_messages as list_gmail_messages,
    reply_to_message as reply_to_gmail_message,
    send_message as send_gmail_message,
)


def _gmail_headers(message):
    return {
        item.get("name", "").lower(): item.get("value", "")
        for item in message.get("payload", {}).get("headers", [])
    }


def _graph_get(user, url, params=None):
    headers = get_graph_headers(user)
    response = requests.get(url, headers=headers, params=params, timeout=20)
    print("GRAPH STATUS:", response.status_code)
    print("GRAPH BODY:", response.text)
    response.raise_for_status()
    return response.json()


def fetch_new_emails(user):
    """Retourne le nombre d'emails non lus dans la boîte de réception."""
    try:
        token = OAuthToken.objects.get(user=user, provider="google")
    except OAuthToken.DoesNotExist:
        return 0

    try:
        del token
        return len(list_gmail_messages(user, label_ids=["INBOX", "UNREAD"], limit=100))
    except Exception as e:
        print(f"Erreur fetch emails Gmail : {e}")
        return 0


def _list_folder_messages(user, folder_name, limit=50, select_fields=None, extra_params=None):
    params = {
        "$top": min(limit, 100),
    }
    if select_fields:
        params["$select"] = select_fields
    if extra_params:
        params.update(extra_params)

    url = f"{GRAPH_URL}/me/mailFolders/{folder_name}/messages"
    headers = get_graph_headers(user)

    results = []

    while url and len(results) < limit:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()

        results.extend(payload.get("value", []))
        url = payload.get("@odata.nextLink")
        params = None  # nextLink contient déjà les paramètres

    return results[:limit]


def check_if_replies_exist(user, limit=200):
    """
    Approximation simple :
    une conversation est considérée comme 'répondue' si on retrouve le conversationId
    dans la boîte de réception.
    """
    try:
        return {
            message.get("threadId")
            for message in list_gmail_messages(user, label_ids=["INBOX"], limit=limit)
            if message.get("threadId")
        }
    except Exception as e:
        print(f"Erreur check_if_replies Gmail : {e}")
        return set()


def get_sent_emails(user, limit=50):
    """Récupère les emails envoyés depuis Gmail."""
    try:
        oauth_token = OAuthToken.objects.get(user=user, provider="google")
    except OAuthToken.DoesNotExist:
        return []

    try:
        replied_ids = check_if_replies_exist(user)
        messages = list_gmail_messages(user, label_ids=["SENT"], limit=limit)

        detailed = []
        for msg in messages:
            headers = _gmail_headers(msg)
            thread_id = msg.get("threadId")
            status = "replied" if thread_id in replied_ids else "pending"
            sent_date_raw = headers.get("date")
            try:
                from email.utils import parsedate_to_datetime
                sent_date = parsedate_to_datetime(sent_date_raw) if sent_date_raw else None
            except (TypeError, ValueError):
                sent_date = None

            detailed.append({
                "id": msg.get("id"),
                "thread_id": thread_id,
                "subject": headers.get("subject") or "(Sans objet)",
                "to": headers.get("to", ""),
                "date": sent_date,
                "body_text": (msg.get("snippet") or "")[:200],
                "from": oauth_token.email,
                "status": status,
                "status_emoji": "✅" if status == "replied" else "⏳",
                "status_text": "Répondu" if status == "replied" else "En attente",
            })

        return detailed

    except Exception as e:
        print(f"Erreur get_sent_emails Gmail : {e}")
        return []


def get_email_summary(email):
    """Normalise la structure pour le template."""
    return {
        "id": email.get("id"),
        "thread_id": email.get("thread_id", ""),
        "subject": email.get("subject", "(Sans objet)"),
        "to": email.get("to", ""),
        "from": email.get("from", ""),
        "date": email.get("date"),
        "body_text": email.get("body_text", ""),
        "status": email.get("status", "pending"),
        "status_emoji": email.get("status_emoji", "⏳"),
        "status_text": email.get("status_text", "En attente"),
    }


def get_message_metadata(user, message_id):
    """Récupère les métadonnées normalisées d'un message Gmail."""
    try:
        message = get_gmail_message(user, message_id)
        headers = _gmail_headers(message)
        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId", ""),
            "subject": headers.get("subject", ""),
            "to": headers.get("to", ""),
            "from": headers.get("from", ""),
            "message_id": headers.get("message-id", ""),
        }
    except Exception as e:
        print(f"Erreur get_message_metadata Gmail : {e}")
        return None


def send_email_reply(user, original_message_id, message_text, subject=None, to_email=None):
    """
    Répond dans le thread Outlook existant si original_message_id est fourni.
    Fallback sur sendMail si besoin.
    """
    try:
        if original_message_id:
            return reply_to_gmail_message(
                user=user,
                message_id=original_message_id,
                body=message_text,
                subject=subject or "",
                to_email=to_email or "",
            )

        if to_email and subject:
            return send_gmail_message(
                user=user,
                to_email=to_email,
                subject=subject,
                body=message_text,
            )

        return {
            "success": False,
            "message": "Aucun message d'origine ni destinataire/sujet fournis.",
        }

    except Exception as e:
        print(f"Erreur send_email_reply : {e}")
        return {
            "success": False,
            "message": str(e),
        }

def send_auto_relance(user, to_email, subject, message_text, objet_custom=None, original_message_id=None):
    """
    Envoie une relance automatique via Outlook / Microsoft Graph.

    Comportement :
    - si objet_custom est fourni, on envoie un nouveau mail avec cet objet
    - sinon, si original_message_id est fourni, on répond dans le thread existant
    - sinon, on envoie un nouveau mail classique
    """
    try:
        final_subject = objet_custom or subject or "Relance"

        if original_message_id and not objet_custom:
            return send_email_reply(
                user=user,
                original_message_id=original_message_id,
                message_text=message_text,
                subject=final_subject,
                to_email=to_email,
            )

        return send_gmail_message(
            user=user,
            to_email=to_email,
            subject=final_subject,
            body=message_text,
        )

    except Exception as e:
        print(f"Erreur send_auto_relance : {e}")
        return {
            "success": False,
            "message": str(e),
        }


def _activity_event_payload(activite):
    start = activite.date
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())

    end = start + timedelta(hours=1)
    subject = activite.titre or f"{activite.type} - {activite.dossier}"

    details = [
        f"Dossier : {activite.dossier}",
        f"Type : {activite.type}",
        f"Statut : {activite.get_statut_display()}",
        f"Priorité : {activite.get_priorite_display()}",
    ]
    if activite.client:
        details.append(f"Client : {activite.client}")
    if activite.contact_externe:
        details.append(f"Contact externe : {activite.contact_externe}")
    if activite.commentaire:
        details.append("")
        details.append(activite.commentaire)

    return {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": "\n".join(details),
        },
        "start": {
            "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Europe/Paris",
        },
        "end": {
            "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Europe/Paris",
        },
    }


def _has_microsoft_sync(user):
    return OAuthToken.objects.filter(user=user, provider="microsoft").exists()


def create_outlook_event(user, activite):
    if not _has_microsoft_sync(user):
        return {
            "success": False,
            "message": "Boîte Microsoft non synchronisée pour cet utilisateur.",
        }

    try:
        response = requests.post(
            f"{GRAPH_URL}/me/events",
            headers=get_graph_headers(user),
            json=_activity_event_payload(activite),
            timeout=20,
        )
        if response.status_code in (200, 201):
            return {
                "success": True,
                "event_id": response.json().get("id", ""),
            }
        return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}


def update_outlook_event(user, activite):
    if not activite.outlook_event_id:
        return {"success": False, "message": "Aucun événement Outlook associé."}

    if not _has_microsoft_sync(user):
        return {
            "success": False,
            "message": "Boîte Microsoft non synchronisée pour cet utilisateur.",
        }

    try:
        response = requests.patch(
            f"{GRAPH_URL}/me/events/{activite.outlook_event_id}",
            headers=get_graph_headers(user),
            json=_activity_event_payload(activite),
            timeout=20,
        )
        if response.status_code in (200, 202):
            return {"success": True, "event_id": activite.outlook_event_id}
        return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}


def delete_outlook_event(user, event_id):
    if not event_id:
        return {"success": True}

    if not _has_microsoft_sync(user):
        return {
            "success": False,
            "message": "Boîte Microsoft non synchronisée pour cet utilisateur.",
        }

    try:
        response = requests.delete(
            f"{GRAPH_URL}/me/events/{event_id}",
            headers=get_graph_headers(user),
            timeout=20,
        )
        if response.status_code in (202, 204, 404):
            return {"success": True}
        return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}
