"""
Gestionnaire de récupération et traitement des emails
"""
from django_mailbox.models import Mailbox, Message
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone


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
    Récupère les nouveaux emails depuis le serveur (INBOX et Sent)
    Retourne le nombre d'emails récupérés
    """
    mailbox = get_or_create_mailbox()

    try:
        # Récupère les emails reçus (INBOX) - convertir le générateur en liste
        inbox_messages = list(mailbox.get_new_mail())
        print(f"✅ {len(inbox_messages)} nouveaux emails reçus (INBOX)")

        # Pour récupérer les emails envoyés, il faut créer une connexion IMAP manuelle
        # car django-mailbox ne supporte pas nativement les autres dossiers
        import imaplib
        import email as email_lib
        from email.header import decode_header

        sent_count = 0
        try:
            # Connexion IMAP
            imap = imaplib.IMAP4_SSL('imap-benjaminmail.alwaysdata.net', 993)
            imap.login('benjaminmail@alwaysdata.net', 'Arceus2004')

            # Essaye différents noms de dossier Sent
            for folder_name in ['Sent', 'Sent Items', 'INBOX.Sent', 'Envoyés']:
                try:
                    status, _ = imap.select(f'"{folder_name}"', readonly=True)
                    if status == 'OK':
                        # Liste les emails
                        _, message_numbers = imap.search(None, 'ALL')

                        for num in message_numbers[0].split():
                            _, msg_data = imap.fetch(num, '(RFC822)')
                            email_body = msg_data[0][1]
                            email_message = email_lib.message_from_bytes(email_body)

                            # Crée un objet Message django-mailbox si besoin
                            # Pour l'instant on compte juste
                            sent_count += 1

                        print(f"✅ {sent_count} emails dans le dossier '{folder_name}'")
                        break
                except Exception as e:
                    continue

            imap.logout()
        except Exception as e:
            print(f"⚠️ Impossible de récupérer le dossier Sent: {e}")

        total = len(inbox_messages) + sent_count
        print(f"📊 Total: {total} emails analysés")
        return total

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des emails: {e}")
        import traceback
        traceback.print_exc()
        return 0


def get_all_emails(limit=50):
    """
    Récupère tous les emails REÇUS stockés dans la base de données
    Exclut les emails envoyés pour n'afficher que ceux à traiter

    Args:
        limit (int): Nombre maximum d'emails à retourner

    Returns:
        QuerySet: Liste des emails triés par date (plus récents en premier)
    """
    # Filtre pour ne récupérer que les emails REÇUS (pas ceux envoyés par nous)
    messages = Message.objects.exclude(
        from_header__icontains='benjaminmail@alwaysdata.net'
    ).order_by('-processed')[:limit]

    return messages


def check_if_replied(message):
    """
    Vérifie si un email reçu a été répondu en cherchant un email envoyé
    avec in_reply_to_id pointant vers cet email

    Args:
        message (Message): Email reçu

    Returns:
        bool: True si répondu, False sinon
    """
    # Cherche un email envoyé par nous qui répond à ce message
    reply_exists = Message.objects.filter(
        from_header__icontains='benjaminmail@alwaysdata.net',  # Envoyé par nous
        in_reply_to_id=message.id  # Qui répond à cet email
    ).exists()

    return reply_exists


def get_email_summary(message):
    """
    Retourne un résumé formaté d'un email avec son statut calculé dynamiquement

    Args:
        message (Message): Objet Message de django-mailbox

    Returns:
        dict: Dictionnaire avec les infos principales de l'email
    """
    # Vérifie si l'email a été répondu
    is_replied = check_if_replied(message)

    # Détermine l'emoji et le texte selon le statut
    if is_replied:
        status_emoji = '✅'
        status_text = 'Répondu'
        status = 'replied'
    else:
        status_emoji = '⏳'
        status_text = 'En attente'
        status = 'pending'

    return {
        'id': message.id,
        'subject': message.subject,
        'from': message.from_header,
        'to': message.to_header,
        'date': message.processed,
        'body_text': message.text[:200] if message.text else '',
        'body_html': message.html,
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
        # Récupère le message original
        print("📧 Récupération du message original...")
        original_message = Message.objects.get(id=original_message_id)
        print(f"✅ Message original trouvé : {original_message.subject}")

        # Ajoute "Re:" au sujet si pas déjà présent
        if not subject.startswith('Re:'):
            subject = f"Re: {subject}"

        # 1. CRÉER L'OBJET MESSAGE DANS LA BD D'ABORD
        print("\n💾 CRÉATION DE L'OBJET MESSAGE DANS LA BD")
        print("-" * 60)

        from django.utils import timezone
        import hashlib

        mailbox = get_or_create_mailbox()

        # Génère un message_id unique
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
            body=message_text,  # TEXT, pas bytes
            encoded=False,
            processed=timezone.now(),
            read=timezone.now(),  # Marqué comme lu immédiatement
            in_reply_to_id=original_message.id,  # Lien vers l'email original
        )

        print(f"✅✅✅ Message enregistré en BD ! ID: {sent_message.id}")
        print(f"       in_reply_to_id: {sent_message.in_reply_to_id}")

        # 2. ENVOYER L'EMAIL VIA SMTP
        print("\n📮 ENVOI DE L'EMAIL VIA SMTP")
        print("-" * 60)

        email = EmailMessage(
            subject=subject,
            body=message_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )

        # Ajoute les headers pour marquer comme réponse
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


