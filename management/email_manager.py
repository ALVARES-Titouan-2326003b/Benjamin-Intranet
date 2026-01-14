"""
Gestionnaire d'emails via Microsoft Graph API
Fonctions pour lire, envoyer et gérer les emails Outlook/Microsoft 365
"""
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from .oauth_utils import get_access_token


def fetch_new_emails(user, limit=50):
    """
    Récupère les nouveaux emails de la boîte de réception (INBOX)

    Args:
        user (User): Utilisateur Django
        limit (int): Nombre maximum d'emails à récupérer

    Returns:
        list: Liste des emails récupérés
    """
    try:
        access_token = get_access_token(user)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        params = {
            '$top': limit,
            '$select': 'id,subject,from,toRecipients,receivedDateTime,bodyPreview,conversationId',
            '$orderby': 'receivedDateTime desc'
        }

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages',
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            print(f"Erreur lors de la récupération des emails INBOX: {response.status_code}")
            print(f"Détails: {response.text}")
            return []

        data = response.json()
        messages = data.get('value', [])

        print(f"Récupération INBOX: {len(messages)} emails")

        return messages

    except Exception as e:
        print(f"Erreur dans fetch_new_emails: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_sent_emails(user, limit=50):
    """
    Récupère les emails envoyés (SENT)
    Détecte automatiquement le statut (répondu/en attente) via conversationId

    Args:
        user (User): Utilisateur Django
        limit (int): Nombre maximum d'emails à récupérer

    Returns:
        list: Liste des emails avec statut
    """
    try:
        access_token = get_access_token(user)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Récupérer les conversationIds des emails reçus (pour détection réponses)
        replied_conversation_ids = check_if_replies_exist(user)

        # Récupérer les emails envoyés
        params = {
            '$top': limit,
            '$select': 'id,subject,toRecipients,sentDateTime,bodyPreview,conversationId',
            '$orderby': 'sentDateTime desc'
        }

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/mailFolders/SentItems/messages',
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            print(f"Erreur lors de la récupération des emails SENT: {response.status_code}")
            print(f"Détails: {response.text}")
            return []

        data = response.json()
        messages = data.get('value', [])

        # Enrichir avec le statut
        formatted_messages = []
        for msg in messages:
            conversation_id = msg.get('conversationId')

            # Déterminer le statut
            if conversation_id and conversation_id in replied_conversation_ids:
                status = 'replied'
                status_emoji = '✅'
                status_text = 'Répondu'
            else:
                status = 'pending'
                status_emoji = '⏳'
                status_text = 'En attente'

            # Extraire les informations
            to_recipients = msg.get('toRecipients', [])
            to_email = to_recipients[0]['emailAddress']['address'] if to_recipients else ''

            formatted_messages.append({
                'id': msg.get('id'),
                'conversation_id': conversation_id,
                'subject': msg.get('subject', '(Sans objet)'),
                'to': to_email,
                'date': msg.get('sentDateTime'),
                'body_preview': msg.get('bodyPreview', ''),
                'status': status,
                'status_emoji': status_emoji,
                'status_text': status_text
            })

        print(f"Récupération SENT: {len(formatted_messages)} emails")
        pending_count = sum(1 for m in formatted_messages if m['status'] == 'pending')
        replied_count = sum(1 for m in formatted_messages if m['status'] == 'replied')
        print(f"  - {pending_count} en attente")
        print(f"  - {replied_count} répondus")

        return formatted_messages

    except Exception as e:
        print(f"Erreur dans get_sent_emails: {e}")
        import traceback
        traceback.print_exc()
        return []


def check_if_replies_exist(user, limit=100):
    """
    Récupère tous les conversationIds des emails reçus (INBOX)
    Utilisé pour détecter si un email envoyé a reçu une réponse

    Logique: Si conversationId(SENT) existe dans INBOX = réponse reçue

    Args:
        user (User): Utilisateur Django
        limit (int): Nombre maximum d'emails INBOX à analyser

    Returns:
        set: Ensemble des conversationIds présents dans INBOX
    """
    try:
        access_token = get_access_token(user)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        params = {
            '$top': limit,
            '$select': 'conversationId',
            '$orderby': 'receivedDateTime desc'
        }

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages',
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            print(f"Erreur lors de la vérification des réponses: {response.status_code}")
            return set()

        data = response.json()
        messages = data.get('value', [])

        # Extraire tous les conversationIds
        conversation_ids = set()
        for msg in messages:
            conversation_id = msg.get('conversationId')
            if conversation_id:
                conversation_ids.add(conversation_id)

        print(f"Vérification des réponses: {len(conversation_ids)} conversations trouvées dans INBOX")

        return conversation_ids

    except Exception as e:
        print(f"Erreur dans check_if_replies_exist: {e}")
        import traceback
        traceback.print_exc()
        return set()


def send_email_reply(to_email, subject, message_text, original_message_id=None, user=None):
    """
    Envoie un email de réponse manuelle

    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email
        message_text (str): Corps du message (texte brut)
        original_message_id (str): ID du message original (optionnel)
        user (User): Utilisateur Django

    Returns:
        dict: {'success': bool, 'message': str, 'message_id': str (optionnel)}
    """
    try:
        access_token = get_access_token(user)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Construire le message
        email_message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": message_text
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            },
            "saveToSentItems": True
        }

        # Envoyer l'email
        response = requests.post(
            'https://graph.microsoft.com/v1.0/me/sendMail',
            headers=headers,
            json=email_message
        )

        if response.status_code in [200, 202]:
            print(f"Email envoyé avec succès vers: {to_email}")
            print(f"Sujet: {subject}")
            return {
                'success': True,
                'message': 'Email envoyé avec succès'
            }
        else:
            print(f"Erreur lors de l'envoi de l'email: {response.status_code}")
            print(f"Détails: {response.text}")
            return {
                'success': False,
                'message': f'Erreur lors de l\'envoi: {response.text}'
            }

    except Exception as e:
        print(f"Erreur dans send_email_reply: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Erreur: {str(e)}'
        }


def send_auto_relance(to_email, subject, message_text, objet_custom=None, original_message_id=None, user=None):
    """
    Envoie une relance automatique
    Identique à send_email_reply mais avec un objet personnalisé optionnel

    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet original de l'email
        message_text (str): Message de relance
        objet_custom (str): Objet personnalisé (optionnel)
        original_message_id (str): ID du message original (optionnel)
        user (User): Utilisateur Django

    Returns:
        dict: {'success': bool, 'message': str}
    """
    # Utiliser l'objet personnalisé si fourni, sinon "RE: sujet original"
    if objet_custom:
        final_subject = objet_custom
    else:
        final_subject = f"RE: {subject}" if not subject.startswith("RE:") else subject

    return send_email_reply(
        to_email=to_email,
        subject=final_subject,
        message_text=message_text,
        original_message_id=original_message_id,
        user=user
    )


def get_email_summary(email_data):
    """
    Formate les données d'un email pour l'affichage dans l'interface
    Compatible avec la structure Microsoft Graph

    Args:
        email_data (dict): Données de l'email depuis Microsoft Graph

    Returns:
        dict: Email formaté pour l'affichage
    """
    return {
        'id': email_data.get('id'),
        'subject': email_data.get('subject', '(Sans objet)'),
        'to': email_data.get('to', ''),
        'date': email_data.get('date'),
        'body_preview': email_data.get('body_preview', ''),
        'status': email_data.get('status', 'pending'),
        'status_emoji': email_data.get('status_emoji', '⏳'),
        'status_text': email_data.get('status_text', 'En attente')
    }


def mark_as_read(message_id, user):
    """
    Marque un email comme lu

    Args:
        message_id (str): ID du message Microsoft Graph
        user (User): Utilisateur Django

    Returns:
        bool: True si succès, False sinon
    """
    try:
        access_token = get_access_token(user)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        data = {
            "isRead": True
        }

        response = requests.patch(
            f'https://graph.microsoft.com/v1.0/me/messages/{message_id}',
            headers=headers,
            json=data
        )

        if response.status_code in [200, 204]:
            print(f"Message marqué comme lu: {message_id}")
            return True
        else:
            print(f"Erreur lors du marquage comme lu: {response.status_code}")
            return False

    except Exception as e:
        print(f"Erreur dans mark_as_read: {e}")
        return False


def get_sent_emails_for_celery(user, limit=100):
    """
    Version simplifiée de get_sent_emails pour utilisation dans les tâches Celery
    Récupère les emails des 90 derniers jours uniquement

    Args:
        user (User): Utilisateur Django
        limit (int): Nombre maximum d'emails

    Returns:
        list: Liste d'emails avec statut
    """
    try:
        access_token = get_access_token(user)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Date limite : 90 jours
        date_limite = timezone.now() - timedelta(days=90)
        date_limite_iso = date_limite.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Récupérer les conversationIds des emails reçu
        replied_conversation_ids = check_if_replies_exist(user)

        # Récupérer les emails envoyés des 90 derniers jours
        params = {
            '$top': limit,
            '$select': 'id,subject,toRecipients,sentDateTime,conversationId',
            '$orderby': 'sentDateTime desc',
            '$filter': f"sentDateTime ge {date_limite_iso}"
        }

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/mailFolders/SentItems/messages',
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            print(f"Erreur get_sent_emails_for_celery: {response.status_code}")
            return []

        data = response.json()
        messages = data.get('value', [])

        # Formater les messages
        detailed_messages = []
        for msg in messages:
            conversation_id = msg.get('conversationId')

            # Déterminer le statut
            status = 'pending'
            if conversation_id and conversation_id in replied_conversation_ids:
                status = 'replied'

            # Extraire les informations
            to_recipients = msg.get('toRecipients', [])
            to_email = to_recipients[0]['emailAddress']['address'] if to_recipients else ''

            # Convertir la date
            sent_datetime_str = msg.get('sentDateTime')
            try:
                sent_datetime = datetime.fromisoformat(sent_datetime_str.replace('Z', '+00:00'))
            except:
                sent_datetime = timezone.now()

            detailed_messages.append({
                'id': msg.get('id'),
                'conversation_id': conversation_id,
                'subject': msg.get('subject', '(Sans objet)'),
                'to': to_email,
                'date': sent_datetime,
                'status': status
            })

        return detailed_messages

    except Exception as e:
        print(f"Erreur dans get_sent_emails_for_celery: {e}")
        import traceback
        traceback.print_exc()
        return []