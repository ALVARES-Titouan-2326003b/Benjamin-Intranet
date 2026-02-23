"""
Gestionnaire de récupération et traitement des emails
"""
import base64
from django.utils import timezone
from management.modelsadm import OAuthToken
import traceback


def fetch_new_emails(user):
    """
    Récupère les nouveaux emails via Gmail API avec OAuth2

    Args:
        user (User): L'utilisateur Django connecté

    Returns:
        int: Nombre d'emails récupérés
    """
    try:
        oauth_token = OAuthToken.objects.get(user=user)
    except OAuthToken.DoesNotExist:
        print(f"{user.username} n'a pas synchronisé sa boîte mail")
        return 0

    print(f"\nRécupération des emails pour {user.username} ({oauth_token.email})...")

    try:
        from management.oauth_utils import get_gmail_service

        service = get_gmail_service(user)

        results = service.users().messages().list(
            userId='me',
            maxResults=100,
            labelIds=['INBOX']
        ).execute()

        messages = results.get('messages', [])

        print(f"{len(messages)} messages trouvés dans INBOX")

        return len(messages)

    except Exception as e:
        print(f"Erreur récupération emails : {e}")
        import traceback
        traceback.print_exc()
        return 0


def get_sent_emails(user, limit=50):
    """
    Récupère les emails ENVOYÉS via Gmail API avec détection du statut (répondu/en attente)

    Args:
        user (User): L'utilisateur Django connecte
        limit (int): Nombre maximum d'emails a retourner

    Returns:
        list: Liste des emails envoyés avec leurs détails et statut
    """
    try:
        oauth_token = OAuthToken.objects.get(user=user)
    except OAuthToken.DoesNotExist:
        print(f"{user.username} n'a pas synchronisé sa boîte mail")
        return []

    try:
        from management.oauth_utils import get_gmail_service

        service = get_gmail_service(user)

        results = service.users().messages().list(
            userId='me',
            maxResults=limit,
            labelIds=['SENT']
        ).execute()

        messages = results.get('messages', [])

        print(f"\nRécupération de {len(messages)} emails envoyés...")
        replied_message_ids = check_if_replies_exist(user)

        detailed_messages = []

        for msg in messages:
            try:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Sans objet)')
                to = next((h['value'] for h in headers if h['name'] == 'To'), '')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                #message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)

                from email.utils import parsedate_to_datetime
                try:
                    date = parsedate_to_datetime(date_str)
                except (TypeError, ValueError):
                    date = timezone.now()

                body = ''
                if 'parts' in msg_data['payload']:
                    for part in msg_data['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            if 'data' in part['body']:
                                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                break
                elif 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                    body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8')

                thread_id = msg_data.get('threadId')

                status = 'pending'
                status_emoji = '⏳'
                status_text = 'En attente'

                if thread_id and thread_id in replied_message_ids:
                    status = 'replied'
                    status_emoji = '✅'
                    status_text = 'Répondu'

                detailed_messages.append({
                    'id': msg['id'],
                    'subject': subject,
                    'to': to,
                    'date': date,
                    'body_text': body[:200] if body else '',
                    'from': oauth_token.email,
                    'status': status,
                    'status_emoji': status_emoji,
                    'status_text': status_text
                })
            except Exception as e:
                print(f"Erreur sur le message {msg['id']}: {e}")
                continue

        print(f"{len(detailed_messages)} emails envoyés récupérés")

        replied_count = sum(1 for m in detailed_messages if m['status'] == 'replied')
        pending_count = sum(1 for m in detailed_messages if m['status'] == 'pending')
        print(f"   Statuts : {replied_count} répondus, {pending_count} en attente")

        return detailed_messages

    except Exception as e:
        print(f"Erreur récupération emails envoyés : {e}")
        traceback.print_exc()
        return []


def send_email_reply(to_email, subject, message_text, original_message_id, user):
    """
    Envoi un email via Gmail API avec OAuth2

    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email
        message_text (str): Contenu du message
        original_message_id (str): ID du message original (Gmail ID)
        user (User): L'utilisateur Django connecté qui envoie le mail

    Returns:
        dict: {'success': bool, 'message': str}
    """
    print("\nEnvoi email via Gmail API")
    print(f"   User: {user.username}")
    print(f"   To: {to_email}")
    print(f"   Subject: {subject}")

    try:
        oauth_token = OAuthToken.objects.get(user=user)

        if not subject.startswith('Re:'):
            subject = f"Re: {subject}"

        from management.oauth_utils import send_email_via_gmail_api

        result = send_email_via_gmail_api(user, to_email, subject, message_text)

        if result['success']:
            print(f"Email envoyé avec succès depuis {oauth_token.email}")
            return {
                'success': True,
                'message': 'Email envoyé avec succès !'
            }
        else:
            print(f"Échec envoi : {result.get('error')}")
            return {
                'success': False,
                'message': f"Erreur : {result.get('error')}"
            }

    except OAuthToken.DoesNotExist:
        return {
            'success': False,
            'message': 'Vous devez synchroniser votre boîte mail Gmail avant d\'envoyer des emails'
        }
    except Exception as e:
        print(f"Erreur : {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Erreur : {str(e)}'
        }


def send_auto_relance(to_email, subject, message_text, objet_custom, original_message_id, user):
    """
    Envoie une RELANCE AUTOMATIQUE via Gmail API

    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email original
        message_text (str): Contenu du message personnalisé
        objet_custom (str): Objet personnalisé
        original_message_id (str): ID du message original (Gmail ID)
        user (User): L'utilisateur Django connecté

    Returns:
        dict: {'success': bool, 'message': str}
    """
    print("\nEnvoi relance automatique via Gmail API")
    print(f"   User: {user.username}")
    print(f"   To: {to_email}")

    if objet_custom:
        final_subject = f"{objet_custom}: relance automatique"
    else:
        base_subject = subject.replace('Re: ', '', 1) if subject.startswith('Re:') else subject
        final_subject = f"{base_subject}: relance automatique"

    return send_email_reply(to_email, final_subject, message_text, original_message_id, user)


def check_if_replies_exist(user):
    """
    VERSION 2 : Utilise threadId pour détecter les conversations avec réponses
    """
    try:
        from management.oauth_utils import get_gmail_service

        service = get_gmail_service(user)

        print("\nVérification des réponses (méthode threadId)...")

        results = service.users().messages().list(
            userId='me',
            maxResults=100,
            labelIds=['INBOX']
        ).execute()

        inbox_messages = results.get('messages', [])
        print(f"   {len(inbox_messages)} messages dans INBOX")

        inbox_thread_ids = set()
        for msg in inbox_messages:
            thread_id = msg.get('threadId')
            if thread_id:
                inbox_thread_ids.add(thread_id)

        print(f"   {len(inbox_thread_ids)} threads trouvés dans INBOX")

        return inbox_thread_ids

    except Exception as e:
        print(f"   Erreur check_if_replies_exist: {e}")
        import traceback
        traceback.print_exc()
        return set()


def check_if_received_reply(sent_message, user):
    """
    Vérifie si un email ENVOYÉ a reçu une réponse

    Args:
        sent_message (dict): Email envoyé avec au minimum {'id': gmail_id}
        user (User): Utilisateur Django

    Returns:
        bool: True si réponse reçue, False sinon
    """
    try:
        from management.oauth_utils import get_gmail_service

        service = get_gmail_service(user)

        msg_data = service.users().messages().get(
            userId='me',
            id=sent_message['id'],
            format='metadata',
            metadataHeaders=['Message-ID']
        ).execute()

        headers = msg_data['payload']['headers']
        message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)

        if not message_id:
            return False

        clean_message_id = message_id.strip().strip('<>')

        query = f'in:inbox (in-reply-to:{clean_message_id} OR references:{clean_message_id})'

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()

        messages = results.get('messages', [])

        return len(messages) > 0

    except Exception as e:
        print(f"   Erreur check_if_received_reply: {e}")
        return False




def get_email_summary(email_dict):
    """
    Retourne un résumé formaté d'un email
    (Déjà formaté par get_sent_emails, donc on le retourne tel quel)

    Args:
        email_dict (dict): Dictionnaire contenant les infos de l'email

    Returns:
        dict: Résumé de l'email formaté
    """
    if isinstance(email_dict, dict):
        return email_dict

    return {
        'id': getattr(email_dict, 'id', ''),
        'subject': getattr(email_dict, 'subject', '(Sans objet)'),
        'from': getattr(email_dict, 'from_header', ''),
        'to': getattr(email_dict, 'to_header', ''),
        'date': getattr(email_dict, 'processed', timezone.now()),
        'body_text': '',
        'status': 'pending',
        'status_emoji': '⏳',
        'status_text': 'En attente'
    }