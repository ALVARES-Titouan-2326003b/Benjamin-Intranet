"""
VERSION DEBUG ULTRA-DÉTAILLÉ
Cette version affiche EXACTEMENT où chaque email est bloqué
"""
import os
from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from .modelsadm import Utilisateur, Modele_Relance, Temps_Relance, Activites, OAuthToken
from .email_manager import send_auto_relance
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
import logging
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


@shared_task
def check_and_send_auto_relances():
    """
    VERSION DEBUG ULTRA-DÉTAILLÉ
    """
    print("\n" + "=" * 80)
    print("VERSION DEBUG ULTRA-DÉTAILLÉ")
    print(f"Date d'exécution : {timezone.now()}")
    print("=" * 80)

    today = timezone.now().date()
    relances_envoyees = 0
    emails_traites = 0
    erreurs = 0

    # Compteurs de debug
    blocked_at = {
        'status_replied': 0,
        'date_missing': 0,
        'nb_jours_check': 0,
        'email_missing': 0,
        'utilisateur_not_found': 0,
        'temps_relance_not_found': 0,
        'modulo_check': 0,
        'modele_relance_not_found': 0,
        'message_empty': 0,
        'sent_successfully': 0,
        'send_failed': 0
    }

    try:
        oauth_users = OAuthToken.objects.all()

        if oauth_users.count() == 0:
            print("\nAucun utilisateur avec token OAuth trouvé")
            return {
                'success': True,
                'emails_traites': 0,
                'relances_envoyees': 0,
                'erreurs': 0
            }

        print(f"\n{oauth_users.count()} utilisateur(s) avec token OAuth")

        for oauth_token in oauth_users:
            user = oauth_token.user
            print(f"\n{'='*70}")
            print(f"Traitement de {user.username} ({oauth_token.email})")
            print(f"{'='*70}")

            try:
                sent_emails = get_sent_emails_for_celery(user, limit=100)

                print(f"   {len(sent_emails)} emails trouvés dans SENT")

                pending_count = sum(1 for e in sent_emails if e.get('status') == 'pending')
                replied_count = sum(1 for e in sent_emails if e.get('status') == 'replied')
                print(f"   └─ {pending_count} en attente, {replied_count} répondus")

                # DEBUG : Afficher les détails de chaque email
                print(f"\n   ANALYSE DÉTAILLÉE DE CHAQUE EMAIL:")
                print(f"   {'─'*66}")

                for idx, email_data in enumerate(sent_emails, 1):
                    emails_traites += 1

                    print(f"\n   Email #{idx}/{len(sent_emails)}")
                    print(f"      Sujet: {email_data.get('subject', '(Sans objet)')[:50]}")
                    print(f"      To: {email_data.get('to', 'N/A')[:50]}")

                    try:
                        # CHECK 1 : Statut
                        status = email_data.get('status', 'pending')
                        print(f"      └─ Statut: {status}")

                        if status != 'pending':
                            print(f"         BLOQUÉ : Email déjà répondu")
                            blocked_at['status_replied'] += 1
                            continue

                        # CHECK 2 : Date
                        date_envoi = email_data.get('date')
                        if not date_envoi:
                            print(f"         BLOQUÉ : Pas de date d'envoi")
                            blocked_at['date_missing'] += 1
                            continue

                        if hasattr(date_envoi, 'date'):
                            date_envoi = date_envoi.date()

                        nb_jours = (today - date_envoi).days
                        print(f"      └─ Date envoi: {date_envoi}")
                        print(f"      └─ Jours écoulés: {nb_jours}")

                        print(f"      └─ Test: nb_jours < 0 ? {nb_jours < 0}")
                        if nb_jours < 1:
                            print(f"         BLOQUÉ : nb_jours >= 0 (ligne 105)")
                            blocked_at['nb_jours_check'] += 1
                            continue

                        print(f"      └─ Passé le check nb_jours")

                        destinataire_email = email_data.get('to', '')

                        if not destinataire_email:
                            print(f"         BLOQUÉ : Pas de destinataire")
                            blocked_at['email_missing'] += 1
                            continue

                        if '<' in destinataire_email and '>' in destinataire_email:
                            destinataire_email = destinataire_email.split('<')[1].split('>')[0].strip()

                        print(f"      └─ Destinataire nettoyé: {destinataire_email}")

                        try:
                            utilisateur = Utilisateur.objects.get(email=destinataire_email)
                            print(f"      └─ Utilisateur trouvé: {utilisateur.nom} (ID: {utilisateur.id})")
                        except Utilisateur.DoesNotExist:
                            print(f"         BLOQUÉ : Utilisateur '{destinataire_email}' pas dans table Utilisateur")
                            blocked_at['utilisateur_not_found'] += 1
                            continue

                        try:
                            temps_relance = Temps_Relance.objects.get(id=utilisateur.id)
                            intervalle = temps_relance.relance
                            print(f"      └─ Intervalle de relance: {intervalle} jours")
                        except Temps_Relance.DoesNotExist:
                            print(f"         BLOQUÉ : Pas de Temps_Relance pour utilisateur ID {utilisateur.id}")
                            blocked_at['temps_relance_not_found'] += 1
                            continue


                        if nb_jours % intervalle != 0:
                            print(f"         BLOQUÉ : {nb_jours} n'est pas un multiple de {intervalle}")
                            blocked_at['modulo_check'] += 1
                            continue

                        print(f"      └─ Passé le check modulo")

                        try:
                            modele_relance = Modele_Relance.objects.get(utilisateur=utilisateur.id)
                            message_relance = modele_relance.message
                            objet_relance = modele_relance.objet
                            print(f"      └─ Modèle de relance trouvé")
                            print(f"         Objet: {objet_relance[:30] if objet_relance else 'N/A'}...")
                        except Modele_Relance.DoesNotExist:
                            print(f"         BLOQUÉ : Pas de Modele_Relance pour utilisateur ID {utilisateur.id}")
                            blocked_at['modele_relance_not_found'] += 1
                            continue

                        # CHECK 9 : Message vide
                        if not message_relance:
                            print(f"         BLOQUÉ : Message de relance vide")
                            blocked_at['message_empty'] += 1
                            continue

                        print(f"      └─ Message: {message_relance[:50]}...")

                        print(f"\n      TOUS LES CHECKS PASSÉS ! ENVOI EN COURS...")

                        result = send_auto_relance(
                            to_email=destinataire_email,
                            subject=email_data.get('subject', '(Sans objet)'),
                            message_text=message_relance,
                            objet_custom=objet_relance,
                            original_message_id=email_data.get('id'),
                            user=user
                        )

                        if result['success']:
                            print(f"         RELANCE ENVOYÉE !")
                            blocked_at['sent_successfully'] += 1
                            relances_envoyees += 1
                        else:
                            print(f"         ÉCHEC ENVOI : {result['message']}")
                            blocked_at['send_failed'] += 1
                            erreurs += 1

                    except Exception as e:
                        print(f"         ERREUR EXCEPTION : {e}")
                        import traceback
                        traceback.print_exc()
                        erreurs += 1
                        continue

            except Exception as e:
                print(f"   Erreur pour {user.username} : {e}")
                import traceback
                traceback.print_exc()
                continue


        print("\n" + "=" * 80)
        print("RAPPORT DEBUG ULTRA-DÉTAILLÉ")
        print("=" * 80)
        print(f"Emails traités : {emails_traites}")
        print(f"Relances envoyées : {relances_envoyees}")
        print(f"Erreurs : {erreurs}")
        print("\nDÉTAIL DES BLOCAGES :")
        print(f"   ├─ Emails répondus (status != pending) : {blocked_at['status_replied']}")
        print(f"   ├─ Date manquante : {blocked_at['date_missing']}")
        print(f"   ├─ Bloqué par 'nb_jours >= 0' (ligne 105) : {blocked_at['nb_jours_check']}")
        print(f"   ├─ Email destinataire manquant : {blocked_at['email_missing']}")
        print(f"   ├─ Utilisateur pas dans BD : {blocked_at['utilisateur_not_found']}")
        print(f"   ├─ Temps_Relance pas trouvé : {blocked_at['temps_relance_not_found']}")
        print(f"   ├─ Bloqué par modulo (nb_jours % intervalle) : {blocked_at['modulo_check']}")
        print(f"   ├─ Modele_Relance pas trouvé : {blocked_at['modele_relance_not_found']}")
        print(f"   ├─ Message de relance vide : {blocked_at['message_empty']}")
        print(f"   ├─ Relances envoyées avec succès : {blocked_at['sent_successfully']}")
        print(f"   └─ Échecs d'envoi : {blocked_at['send_failed']}")
        print("=" * 80 + "\n")

        return {
            'success': True,
            'emails_traites': emails_traites,
            'relances_envoyees': relances_envoyees,
            'erreurs': erreurs,
            'debug': blocked_at
        }

    except Exception as e:
        print(f"\nERREUR CRITIQUE : {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")

        return {
            'success': False,
            'message': str(e)
        }


def get_sent_emails_for_celery(user, limit=100):
    """
    Permet de récuperer les mails a la place de la bd
    """
    try:
        from management.oauth_utils import get_gmail_service

        service = get_gmail_service(user)

        date_limite = timezone.now() - timedelta(days=90)
        date_limite_str = date_limite.strftime('%Y/%m/%d')

        query = f'in:sent after:{date_limite_str}'

        results = service.users().messages().list(
            userId='me',
            maxResults=limit,
            q=query
        ).execute()

        messages = results.get('messages', [])

        from management.email_manager import check_if_replies_exist
        replied_thread_ids = check_if_replies_exist(user)

        detailed_messages = []

        for msg in messages:
            try:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'To', 'Date']
                ).execute()

                thread_id = msg_data.get('threadId')
                headers = msg_data['payload']['headers']

                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Sans objet)')
                to = next((h['value'] for h in headers if h['name'] == 'To'), '')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')

                try:
                    date = parsedate_to_datetime(date_str)
                except:
                    date = timezone.now()

                status = 'pending'
                if thread_id and thread_id in replied_thread_ids:
                    status = 'replied'

                detailed_messages.append({
                    'id': msg['id'],
                    'thread_id': thread_id,
                    'subject': subject,
                    'to': to,
                    'date': date,
                    'status': status
                })

            except Exception as e:
                continue

        return detailed_messages

    except Exception as e:
        print(f"   ❌ Erreur get_sent_emails_for_celery : {e}")
        return []


@shared_task
def check_and_send_activite_reminders():
    """
    Tâche périodique qui vérifie les activités à venir
    et envoie des rappels 10, 7, 4 et 1 jour(s) avant la date prévue
    INCHANGÉ : Ne nécessite pas de modification pour OAuth2
    """
    logger.info("\n" + "=" * 60)
    logger.info("DÉBUT - Vérification des rappels d'activités")
    logger.info("=" * 60)

    now = datetime.now()
    today = now.date()
    logger.info(f"Date actuelle : {today}")

    # Date limite : dans 10 jours
    date_limite = today + timedelta(days=10)
    logger.info(f"Date limite : {date_limite} (dans 10 jours)")

    # Récupérer toutes les activités dans les 10 prochains jours
    activites = Activites.objects.filter(
        date__date__gt=today,
        date__date__lte=date_limite
    ).order_by('date')

    logger.info(f"📊 Activités trouvées dans les 10 prochains jours : {activites.count()}")

    activites_traitees = 0
    rappels_envoyes = 0

    for activite in activites:
        try:
            activites_traitees += 1

            date_activite = activite.date.date()
            jours_restants = (date_activite - today).days

            logger.info(f"\n📋 Activité #{activite.id}")
            logger.info(f"   Dossier: {activite.dossier}")
            logger.info(f"   Type: {activite.type}")
            logger.info(f"   Date: {date_activite}")
            logger.info(f"   Jours restants: {jours_restants}")

            should_send = False

            if jours_restants in [1, 4, 7, 10]:
                should_send = True
                logger.info(f"   Rappel nécessaire (J-{jours_restants})")
            else:
                logger.info(f"   Pas de rappel pour J-{jours_restants}")

            if should_send:
                # Construire le message
                objet = f"Rappel d'activité - J-{jours_restants}"

                message = f"""Bonjour,

Ceci est un rappel automatique concernant l'activité suivante :

- Dossier : {activite.dossier}
- Type : {activite.type}
- Date prévue : {date_activite.strftime('%d/%m/%Y')}
- Échéance : dans {jours_restants} jour(s)

"""

                if activite.commentaire:
                    message += f"Commentaire : {activite.commentaire}\n\n"

                message += f"""Merci de prendre les dispositions nécessaires.

Cordialement,
Système de rappel Benjamin Immobilier"""

                # Envoyer l'email à l'administrateur
                try:
                    email = EmailMessage(
                        subject=objet,
                        body=message,
                        from_email=os.getenv("EMAIL_HOST_USER"),
                        to=[os.getenv("EMAIL_HOST_USER")],
                    )

                    email.send()
                    rappels_envoyes += 1
                    logger.info(f"   Rappel envoyé avec succès")
                except Exception as e:
                    logger.error(f"   Erreur envoi email : {e}")

        except Exception as e:
            logger.error(f"Erreur traitement activité {activite.id}: {e}")
            import traceback
            traceback.print_exc()
            continue

    logger.info("\n" + "=" * 60)
    logger.info(f"FIN - Rappels d'activités")
    logger.info(f"📊 Résumé :")
    logger.info(f"   - Activités traitées : {activites_traitees}")
    logger.info(f"   - Rappels envoyés : {rappels_envoyes}")
    logger.info("=" * 60 + "\n")

    return {
        'success': True,
        'activites_traitees': activites_traitees,
        'rappels_envoyes': rappels_envoyes
    }