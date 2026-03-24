import os
import logging
import traceback
from datetime import datetime, timedelta

from celery import shared_task
from django.core.mail import EmailMessage
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    DefaultModeleRelance,
    DefaultTempsRelance,
    ModeleRelance,
    TempsRelance,
    EmailClient,
    Activite,
    OAuthToken,
)
from .email_manager import send_auto_relance, get_sent_emails

Utilisateur = get_user_model()

logger = logging.getLogger(__name__)


@shared_task
def check_and_send_auto_relances():



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
        'temps_relance_not_found': 0,
        'default_temps_relance_not_found': False,
        'modulo_check': 0,
        'client_not_found': 0,
        'modele_relance_not_found': 0,
        'default_modele_relance_not_found': 0,
        'message_empty': 0,
        'sent_successfully': 0,
        'send_failed': 0,
        'utilisateur_not_found': 0,
    }

    try:
        oauth_users = OAuthToken.objects.all()

        if oauth_users.count() == 0:
            return {
                'success': True,
                'emails_traites': 0,
                'relances_envoyees': 0,
                'erreurs': 0
            }

        default_temps_relance_obj = DefaultTempsRelance.objects.first()
        default_temps_relance = default_temps_relance_obj.temps if default_temps_relance_obj else None

        if default_temps_relance is None:
            blocked_at['default_temps_relance_not_found'] = True

        for oauth_token in oauth_users:
            user = oauth_token.user
            print(f"Traitement de {user.username} ({oauth_token.email})")


            try:
                sent_emails = get_sent_emails(user, limit=100)

                print(f"   {len(sent_emails)} emails trouvés dans SENT")

                #pending_count = sum(1 for e in sent_emails if e.get('status') == 'pending')
                #replied_count = sum(1 for e in sent_emails if e.get('status') == 'replied')

                print("\n   ANALYSE DÉTAILLÉE DE CHAQUE EMAIL:")
                print(f"   {'─'*66}")

                for idx, email_data in enumerate(sent_emails, 1):
                    emails_traites += 1


                    try:
                        status = email_data.get('status', 'pending')

                        if status != 'pending':
                            blocked_at['status_replied'] += 1
                            continue

                        date_envoi = email_data.get('date')
                        if not date_envoi:
                            blocked_at['date_missing'] += 1
                            continue

                        if hasattr(date_envoi, 'date'):
                            date_envoi = date_envoi.date()
                        nb_jours = (today - date_envoi).days
                        if nb_jours < 1:
                            blocked_at['nb_jours_check'] += 1
                            continue


                        destinataire_email = email_data.get('to', '')

                        if not destinataire_email:
                            blocked_at['email_missing'] += 1
                            continue

                        if '<' in destinataire_email and '>' in destinataire_email:
                            destinataire_email = destinataire_email.split('<')[1].split('>')[0].strip()

                        try:
                            utilisateur = user
                        except Utilisateur.DoesNotExist:
                            blocked_at['utilisateur_not_found'] += 1
                            continue

                        try:
                            intervalle = TempsRelance.objects.get(id=user).temps
                        except TempsRelance.DoesNotExist:
                            blocked_at['temps_relance_not_found'] += 1
                            if blocked_at['default_temps_relance_not_found']:
                                continue
                            intervalle = default_temps_relance

                        if not intervalle or intervalle <= 0:
                            continue


                        if nb_jours % intervalle != 0:
                            blocked_at['modulo_check'] += 1
                            continue

                        emails = EmailClient.objects.filter(email=destinataire_email)

                        if emails.count() == 0:
                            blocked_at['client_not_found'] += 1
                            continue

                        metier = emails.first().metier

                        try:
                            message_relance = ModeleRelance.objects.get(utilisateur=user, metier=metier).message
                        except ModeleRelance.DoesNotExist:
                            blocked_at['modele_relance_not_found'] += 1
                            try:
                                message_relance = DefaultModeleRelance.objects.get(metier=metier).message
                            except DefaultModeleRelance.DoesNotExist:
                                blocked_at['default_modele_relance_not_found'] += 1
                                continue

                        if not message_relance:
                            blocked_at['message_empty'] += 1
                            continue

                        objet_original = email_data.get('subject', '(Sans objet)')
                        objet_relance = f"Relance - {objet_original}"


                        result = send_auto_relance(
                            to_email=destinataire_email,
                            subject=email_data.get('subject', '(Sans objet)'),
                            message_text=message_relance,
                            objet_custom=objet_relance,
                            original_message_id=email_data.get('id'),
                            user=utilisateur
                        )

                        if result['success']:
                            blocked_at['sent_successfully'] += 1
                            relances_envoyees += 1
                        else:
                            blocked_at['send_failed'] += 1
                            erreurs += 1

                    except Exception:
                        traceback.print_exc()
                        erreurs += 1
                        continue

            except Exception as e:
                print(f"   Erreur pour {user.username} : {e}")
                traceback.print_exc()
                continue

        return {
            'success': True,
            'emails_traites': emails_traites,
            'relances_envoyees': relances_envoyees,
            'erreurs': erreurs,
            'debug': blocked_at
        }

    except Exception as e:
        traceback.print_exc()

        return {
            'success': False,
            'message': str(e)
        }


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

    date_limite = today + timedelta(days=10)
    logger.info(f"Date limite : {date_limite} (dans 10 jours)")

    activites = Activite.objects.filter(
        date__date__gt=today,
        date__date__lte=date_limite
    ).order_by('date')

    logger.info(f"Activités trouvées dans les 10 prochains jours : {activites.count()}")

    activites_traitees = 0
    rappels_envoyes = 0

    for activite in activites:
        try:
            activites_traitees += 1

            date_activite = activite.date.date()
            jours_restants = (date_activite - today).days

            logger.info(f"\n Activité #{activite.id}")
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

                message += """Merci de prendre les dispositions nécessaires.

Cordialement,
Système de rappel Benjamin Immobilier"""

                try:
                    email = EmailMessage(
                        subject=objet,
                        body=message,
                        from_email=os.getenv("EMAIL_HOST_USER"),
                        to=[os.getenv("EMAIL_HOST_USER")],
                    )

                    email.send()
                    rappels_envoyes += 1
                    logger.info("   Rappel envoyé avec succès")
                except Exception as e:
                    logger.error(f"   Erreur envoi email : {e}")

        except Exception as e:
            logger.error(f"Erreur traitement activité {activite.id}: {e}")
            traceback.print_exc()
            continue

    logger.info("\n" + "=" * 60)
    logger.info("FIN - Rappels d'activités")
    logger.info("Résumé :")
    logger.info(f"   - Activités traitées : {activites_traitees}")
    logger.info(f"   - Rappels envoyés : {rappels_envoyes}")
    logger.info("=" * 60 + "\n")

    return {
        'success': True,
        'activites_traitees': activites_traitees,
        'rappels_envoyes': rappels_envoyes
    }