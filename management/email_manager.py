import requests
from management.models import OAuthToken
from django.utils.dateparse import parse_datetime
from management.oauth_utils import (
    GRAPH_URL,
    get_graph_headers,
    send_email_via_graph_api,
    refresh_access_token,
)


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
        OAuthToken.objects.get(user=user)
    except OAuthToken.DoesNotExist:
        return 0

    try:
        data = _graph_get(
            user,
            f"{GRAPH_URL}/me/mailFolders/inbox",
            params={"$select": "unreadItemCount"},
        )
        return data.get("unreadItemCount", 0)
    except Exception as e:
        print(f"Erreur fetch emails Outlook : {e}")
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
        messages = _list_folder_messages(
            user=user,
            folder_name="inbox",
            limit=limit,
            select_fields="conversationId",
        )
        return {
            msg["conversationId"]
            for msg in messages
            if msg.get("conversationId")
        }
    except Exception as e:
        print(f"Erreur check_if_replies : {e}")
        return set()


def get_sent_emails(user, limit=50):
    """Récupère les emails envoyés depuis Outlook."""
    try:
        oauth_token = OAuthToken.objects.get(user=user)
    except OAuthToken.DoesNotExist:
        return []

    try:
        replied_ids = check_if_replies_exist(user)

        messages = _list_folder_messages(
            user=user,
            folder_name="sentitems",
            limit=limit,
            select_fields="id,subject,toRecipients,sentDateTime,bodyPreview,conversationId",
            extra_params={"$orderby": "sentDateTime desc"},
        )

        detailed = []
        for msg in messages:
            conversation_id = msg.get("conversationId")
            status = "replied" if conversation_id in replied_ids else "pending"

            to_recipients = msg.get("toRecipients", [])
            first_to = ""
            if to_recipients:
                first_to = to_recipients[0].get("emailAddress", {}).get("address", "")

            sent_date_raw = msg.get("sentDateTime")
            sent_date = parse_datetime(sent_date_raw) if sent_date_raw else None

            detailed.append({
                "id": msg.get("id"),
                "subject": msg.get("subject") or "(Sans objet)",
                "to": first_to,
                "date": sent_date,
                "body_text": (msg.get("bodyPreview") or "")[:200],
                "from": oauth_token.email,
                "status": status,
                "status_emoji": "✅" if status == "replied" else "⏳",
                "status_text": "Répondu" if status == "replied" else "En attente",
            })

        return detailed

    except Exception as e:
        print(f"Erreur get_sent_emails Outlook : {e}")
        return []


def get_email_summary(email):
    """Normalise la structure pour le template."""
    return {
        "id": email.get("id"),
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
    """Récupère les métadonnées d'un message via Graph."""
    try:
        return _graph_get(
            user,
            f"{GRAPH_URL}/me/messages/{message_id}",
            params={
                "$select": "id,subject,toRecipients,from,conversationId,internetMessageId"
            },
        )
    except Exception as e:
        print(f"Erreur get_message_metadata : {e}")
        return None


def send_email_reply(user, original_message_id, message_text, subject=None, to_email=None):
    """
    Répond dans le thread Outlook existant si original_message_id est fourni.
    Fallback sur sendMail si besoin.
    """
    try:
        if original_message_id:
            headers = get_graph_headers(user)
            response = requests.post(
                f"{GRAPH_URL}/me/messages/{original_message_id}/reply",
                headers=headers,
                json={"comment": message_text},
                timeout=20,
            )

            if response.status_code == 202:
                return {
                    "success": True,
                    "message": "Réponse envoyée avec succès dans le thread Outlook.",
                }

            return {
                "success": False,
                "message": response.text,
            }

        if to_email and subject:
            return send_email_via_graph_api(
                user=user,
                to_email=to_email,
                subject=subject,
                message_text=message_text,
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

        return send_email_via_graph_api(
            user=user,
            to_email=to_email,
            subject=final_subject,
            message_text=message_text,
        )

    except Exception as e:
        print(f"Erreur send_auto_relance : {e}")
        return {
            "success": False,
            "message": str(e),
        }