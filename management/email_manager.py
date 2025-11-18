"""
Gestionnaire de récupération et traitement des emails
LOGIQUE INVERSÉE : Affiche les emails ENVOYÉS et vérifie si on a reçu des réponses
VERSION SANS decode_email_header() - POUR TEST
"""
from django_mailbox.models import Mailbox, Message
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
import imaplib
import email as email_lib
from celery import Celery


def get_or_create_mailbox():
    """
    Récupère ou crée la mailbox configurée pour alwaysdata
    """
    mailbox, created = Mailbox.objects.get_or_create(
        name='Benjamin Mail',
        defaults={
            'uri': 'imap+ssl://benjaminmail@alwaysdata.net:Arceus2004@imap-benjaminmail.alwaysdata.net:993',
            'from_email': 'benjaminmail@alwaysdata.net',
            'active': True,
        }
    )

    if created:
        print(f"✅ Mailbox '{mailbox.name}' créée avec succès")

    return mailbox


def fetch_new_emails():
    """
    Récupère les nouveaux emails depuis le serveur (INBOX pour les réponses ET Sent pour nos envois)
    Retourne le nombre d'emails récupérés
    """
    mailbox = get_or_create_mailbox()
    total_fetched = 0

    try:
        # 1. RÉCUPÈRE LES EMAILS REÇUS (INBOX) - pour avoir les réponses
        print("\n📥 Récupération des emails reçus (INBOX)...")
        inbox_messages = list(mailbox.get_new_mail())
        print(f"✅ {len(inbox_messages)} nouveaux emails reçus (INBOX)")
        total_fetched += len(inbox_messages)

        # 2. RÉCUPÈRE ET STOCKE LES EMAILS ENVOYÉS (SENT)
        print("\n📤 Récupération des emails envoyés (SENT)...")
        sent_count = fetch_sent_emails(mailbox)
        print(f"✅ {sent_count} emails envoyés récupérés et stockés")
        total_fetched += sent_count

        print(f"\n📊 Total: {total_fetched} emails synchronisés")
        return total_fetched

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des emails: {e}")
        import traceback
        traceback.print_exc()
        return 0


def fetch_sent_emails(mailbox):
    """
    Récupère les emails du dossier SENT et les stocke dans la base de données
    VERSION SANS decode_email_header() - Récupère les headers BRUTS

    Args:
        mailbox: Objet Mailbox de django-mailbox

    Returns:
        int: Nombre d'emails envoyés récupérés
    """
    sent_count = 0

    try:
        # Connexion IMAP
        imap = imaplib.IMAP4_SSL('imap-benjaminmail.alwaysdata.net', 993)
        imap.login('benjaminmail@alwaysdata.net', 'Arceus2004')

        # Essaye différents noms de dossier Sent
        sent_folder = None
        for folder_name in ['Sent', 'Sent Items', 'INBOX.Sent', 'Envoyés', 'Éléments envoyés']:
            try:
                status, _ = imap.select(f'"{folder_name}"', readonly=True)
                if status == 'OK':
                    sent_folder = folder_name
                    print(f"✅ Dossier trouvé: {folder_name}")
                    break
            except Exception:
                continue

        if not sent_folder:
            print("⚠️ Aucun dossier SENT trouvé")
            imap.logout()
            return 0

        # Liste les emails
        _, message_numbers = imap.search(None, 'ALL')

        for num in message_numbers[0].split():
            try:
                _, msg_data = imap.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email_lib.message_from_bytes(email_body)

                # ⚠️ EXTRACTION DES HEADERS SANS DÉCODAGE
                # On récupère les valeurs brutes, telles quelles
                message_id = email_message.get('Message-ID', '').strip()
                subject = email_message.get('Subject', '')  # ⚠️ BRUT, potentiellement encodé
                from_header = email_message.get('From', '')  # ⚠️ BRUT, potentiellement encodé
                to_header = email_message.get('To', '')  # ⚠️ BRUT, potentiellement encodé
                date_str = email_message.get('Date', '')

                # Génère un message_id si absent
                if not message_id:
                    import hashlib
                    unique_string = f"{subject}-{from_header}-{to_header}-{date_str}"
                    unique_hash = hashlib.md5(unique_string.encode()).hexdigest()
                    message_id = f"<generated-{unique_hash}@benjaminmail.alwaysdata.net>"
                    print(f"   ⚠️ Message-ID absent, généré : {message_id}")

                # Parse le corps du message
                body_text = ''
                body_html = ''

                if email_message.is_multipart():
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        if content_type == 'text/plain':
                            body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        elif content_type == 'text/html':
                            body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                else:
                    body_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

                # Vérifie si le message existe déjà
                message_exists = Message.objects.filter(message_id=message_id).exists()

                print(f"\n📧 Email #{num}")
                print(f"   Sujet (BRUT): {subject[:80]}...")  # ⚠️ Affiche potentiellement encodé
                print(f"   Message-ID: {message_id}")
                print(f"   From (BRUT): {from_header}")  # ⚠️ Affiche potentiellement encodé
                print(f"   To (BRUT): {to_header}")  # ⚠️ Affiche potentiellement encodé
                print(f"   Existe déjà ? {message_exists}")

                if not message_exists:
                    try:
                        # Crée l'objet Message dans la BD
                        # ⚠️ Les headers peuvent être encodés (=?UTF-8?B?...)
                        created_msg = Message.objects.create(
                            mailbox=mailbox,
                            subject=subject,  # ⚠️ Potentiellement encodé
                            message_id=message_id,
                            from_header=from_header,  # ⚠️ Potentiellement encodé
                            to_header=to_header,  # ⚠️ Potentiellement encodé
                            outgoing=True,
                            body=body_html if body_html else body_text,
                            encoded=False,
                            processed=timezone.now(),
                            read=timezone.now(),
                        )
                        sent_count += 1
                        print(f"   ✅ Message créé avec succès (ID: {created_msg.id})")
                    except Exception as create_error:
                        print(f"   ❌ ERREUR lors de la création: {create_error}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"   ⏭️  Message déjà en BD, ignoré")

            except Exception as e:
                print(f"⚠️ Erreur sur un email: {e}")
                continue

        imap.logout()
        return sent_count

    except Exception as e:
        print(f"❌ Erreur lors de la récupération du dossier Sent: {e}")
        import traceback
        traceback.print_exc()
        return 0


def get_sent_emails(limit=50):
    """
    Récupère tous les emails ENVOYÉS stockés dans la base de données

    Args:
        limit (int): Nombre maximum d'emails à retourner

    Returns:
        QuerySet: Liste des emails envoyés triés par date (plus récents en premier)
    """
    messages = Message.objects.filter(
        outgoing=True
    ).order_by('-processed')[:limit]

    return messages


def check_if_received_reply(sent_message):
    """
    LOGIQUE INVERSÉE : Vérifie si on a REÇU une réponse à un email qu'on a ENVOYÉ
    Utilise la relation ForeignKey in_reply_to de django-mailbox

    Args:
        sent_message (Message): Email envoyé par nous

    Returns:
        bool: True si quelqu'un nous a répondu, False sinon
    """
    if not sent_message.message_id:
        return False

    try:
        reply_exists = Message.objects.filter(
            outgoing=False,
            in_reply_to_id=sent_message.id
        ).exists()

        return reply_exists

    except Exception as e:
        print(f"⚠️ Erreur dans check_if_received_reply: {e}")
        return False


def get_email_summary(message):
    """
    Retourne un résumé formaté d'un email ENVOYÉ avec son statut de réponse

    Args:
        message (Message): Objet Message de django-mailbox (email envoyé)

    Returns:
        dict: Dictionnaire avec les infos principales de l'email
    """
    has_received_reply = check_if_received_reply(message)

    if has_received_reply:
        status_emoji = '✅'
        status_text = 'A répondu'
        status = 'replied'
    else:
        status_emoji = '⏳'
        status_text = 'Pas de réponse'
        status = 'pending'

    # Récupération sécurisée du body_text
    body_text = ''
    try:
        if message.text:
            body_text = message.text[:200]
    except Exception:
        try:
            if message.body:
                body_text = str(message.body)[:200]
        except Exception:
            body_text = ''

    # Récupération sécurisée du body_html
    body_html = ''
    try:
        body_html = message.html if message.html else ''
    except Exception:
        body_html = ''

    return {
        'id': message.id,
        'subject': message.subject,  # ⚠️ Peut contenir des caractères encodés
        'from': message.from_header,  # ⚠️ Peut contenir des caractères encodés
        'to': message.to_header,  # ⚠️ Peut contenir des caractères encodés
        'date': message.processed,
        'body_text': body_text,
        'body_html': body_html,
        'read': message.read,
        'status': status,
        'status_emoji': status_emoji,
        'status_text': status_text,
    }


def mark_as_read(message_id):
    """
    Marque un email comme lu

    Args:
        message_id (int): ID du message
    """
    try:
        message = Message.objects.get(id=message_id)
        message.read = True
        message.save()
        return True
    except Message.DoesNotExist:
        return False


def send_email_reply(to_email, subject, message_text, original_message_id):
    """
    Envoie un email de réponse avec les headers appropriés
    ET enregistre l'email envoyé dans la base de données

    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email (avec "Re:" ajouté automatiquement si absent)
        message_text (str): Contenu du message
        original_message_id (int): ID du message original auquel on répond

    Returns:
        dict: {'success': bool, 'message': str}
    """
    print("\n" + "=" * 60)
    print("🚀 DÉBUT send_email_reply()")
    print(f"   to_email: {to_email}")
    print(f"   subject: {subject}")
    print(f"   original_message_id: {original_message_id}")
    print("=" * 60)

    try:
        print("🔧 Récupération du message original...")
        original_message = Message.objects.get(id=original_message_id)
        print(f"✅ Message original trouvé : {original_message.subject}")

        if not subject.startswith('Re:'):
            subject = f"Re: {subject}"

        print("\n💾 CRÉATION DE L'OBJET MESSAGE DANS LA BD")
        print("-" * 60)

        from django.utils import timezone
        import hashlib

        mailbox = get_or_create_mailbox()

        unique_id = hashlib.md5(f"{original_message_id}-{timezone.now()}".encode()).hexdigest()
        generated_message_id = f"<sent-{unique_id}@benjaminmail.alwaysdata.net>"

        print(f"   Mailbox: {mailbox.name} (ID: {mailbox.id})")
        print(f"   Original message ID: {original_message.id}")
        print(f"   Message-ID généré: {generated_message_id}")

        sent_message = Message.objects.create(
            mailbox=mailbox,
            subject=subject,
            message_id=generated_message_id,
            from_header=settings.EMAIL_HOST_USER,
            to_header=to_email,
            outgoing=True,
            body=message_text,
            encoded=False,
            processed=timezone.now(),
            read=timezone.now(),
            in_reply_to_id=original_message.id,
        )

        print(f"✅✅✅ Message enregistré en BD ! ID: {sent_message.id}")
        print(f"       in_reply_to_id: {sent_message.in_reply_to_id}")

        print("\n📮 ENVOI DE L'EMAIL VIA SMTP")
        print("-" * 60)

        email = EmailMessage(
            subject=subject,
            body=message_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )

        email.extra_headers = {
            'In-Reply-To': original_message.message_id,
            'References': original_message.message_id,
            'Message-ID': generated_message_id,
        }

        email.send()
        print(f"✅ Email envoyé à {to_email}")
        print("=" * 60 + "\n")

        return {
            'success': True,
            'message': 'Email envoyé avec succès !'
        }

    except Message.DoesNotExist:
        print("❌ Message original introuvable")
        return {
            'success': False,
            'message': 'Email original introuvable'
        }
    except Exception as e:
        print(f"\n❌❌❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60 + "\n")
        return {
            'success': False,
            'message': f'Erreur : {str(e)}'
        }