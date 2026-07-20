import os
import logging
import traceback
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
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
    HistoriqueRappelActivite,
    RappelActivite,
    OAuthToken,
    GmailConversation,
    GmailConversationEvent,
)
from .gmail_service import send_conversation_reminder, sync_conversation_journal

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
        oauth_users = OAuthToken.objects.filter(provider="google").select_related("user")

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
                sync_conversation_journal(user, limit=100)
                conversations = GmailConversation.objects.filter(
                    owner=user,
                    status__in=["open", "reminded"],
                )

                for conversation in conversations:
                    emails_traites += 1
                    try:
                        date_envoi = conversation.sent_at
                        if not date_envoi:
                            blocked_at['date_missing'] += 1
                            continue

                        if hasattr(date_envoi, 'date'):
                            date_envoi = date_envoi.date()
                        nb_jours = (today - date_envoi).days
                        if nb_jours < 1:
                            blocked_at['nb_jours_check'] += 1
                            continue


                        destinataire_email = conversation.recipient

                        if not destinataire_email:
                            blocked_at['email_missing'] += 1
                            continue

                        if '<' in destinataire_email and '>' in destinataire_email:
                            destinataire_email = destinataire_email.split('<')[1].split('>')[0].strip()

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

                        already_sent_today = GmailConversationEvent.objects.filter(
                            conversation=conversation,
                            event_type="reminder_sent",
                            created_at__date=today,
                        ).exists()
                        if already_sent_today:
                            continue

                        result = send_conversation_reminder(
                            conversation=conversation,
                            user=user,
                            body=message_relance,
                        )

                        if result['success']:
                            blocked_at['sent_successfully'] += 1
                            relances_envoyees += 1
                        else:
                            blocked_at['send_failed'] += 1
                            erreurs += 1

                    except Exception as exc:
                        GmailConversationEvent.objects.create(
                            conversation=conversation,
                            event_type="error",
                            user=user,
                            note=str(exc),
                        )
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
    Tâche périodique qui vérifie les activités et envoie les rappels configurés
    sans doublon.
    """
    logger.info("\n" + "=" * 60)
    logger.info("DÉBUT - Vérification des rappels d'activités")
    logger.info("=" * 60)

    today = timezone.localdate()
    logger.info(f"Date actuelle : {today}")

    planned_reminders = list(
        RappelActivite.objects.filter(
            is_active=True,
            activite__date__isnull=False,
        )
        .exclude(activite__statut__in=["done", "cancelled"])
        .select_related(
            "activite",
            "activite__dossier",
            "activite__type",
            "activite__responsable",
            "activite__created_by",
        )
        .order_by("activite__date", "timing", "days")
    )
    if not planned_reminders:
        logger.info("Aucun rappel individuel actif.")
        return {
            'success': True,
            'activites_traitees': 0,
            'rappels_envoyes': 0,
            'doublons_ignores': 0,
            'erreurs': 0,
        }

    logger.info(f"Rappels individuels actifs : {len(planned_reminders)}")

    activites_traitees = 0
    rappels_envoyes = 0
    doublons_ignores = 0
    erreurs = 0

    processed_activity_ids = set()
    for reminder in planned_reminders:
        activite = reminder.activite
        try:
            if activite.pk not in processed_activity_ids:
                activites_traitees += 1
                processed_activity_ids.add(activite.pk)

            date_activite = timezone.localtime(activite.date).date()
            jours_restants = (date_activite - today).days

            logger.info(f"\n Activité #{activite.id}")
            logger.info(f"   Dossier: {activite.dossier}")
            logger.info(f"   Type: {activite.type}")
            logger.info(f"   Date: {date_activite}")
            logger.info(f"   Jours restants: {jours_restants}")

            matches_today = (
                reminder.timing == "before" and jours_restants == reminder.days
            ) or (
                reminder.timing == "after" and jours_restants == -reminder.days
            )
            if not matches_today:
                logger.info("   Pas de rappel configuré pour cette échéance")
                continue

            for rule in [reminder]:
                recipient_email = ""
                if activite.responsable and activite.responsable.email:
                    recipient_email = activite.responsable.email
                elif activite.created_by and activite.created_by.email:
                    recipient_email = activite.created_by.email
                else:
                    recipient_email = getattr(settings, "EMAIL_HOST_USER", "") or os.getenv("EMAIL_HOST_USER", "")

                if not recipient_email:
                    logger.warning("   Aucun destinataire email disponible")
                    continue

                email_already_sent = HistoriqueRappelActivite.objects.filter(
                    activite=activite,
                    canal="email",
                    destinataire=recipient_email,
                    jours_avant_echeance=rule.signed_days,
                    date_echeance=activite.date,
                    statut="sent",
                ).exists()
                if email_already_sent:
                    doublons_ignores += 1
                    logger.info("   Rappel déjà envoyé, doublon ignoré")
                    continue

                objet = f"Rappel d'activité - {rule.label}"
                if rule.days == 0:
                    echeance_label = "aujourd'hui"
                elif rule.timing == "before":
                    echeance_label = f"dans {rule.days} jour(s)"
                else:
                    echeance_label = f"échue depuis {rule.days} jour(s)"

                message = f"""Bonjour,

Ceci est un rappel automatique concernant l'activité suivante :

- Titre : {activite.titre or activite.type}
- Dossier : {activite.dossier}
- Type : {activite.type}
- Statut : {activite.get_statut_display()}
- Priorité : {activite.get_priorite_display()}
- Date prévue : {date_activite.strftime('%d/%m/%Y')} à {timezone.localtime(activite.date).strftime('%H:%M')}
- Créneau : {activite.get_duree_minutes_display()}
- Échéance : {echeance_label}

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
                        from_email=getattr(settings, "EMAIL_HOST_USER", "") or os.getenv("EMAIL_HOST_USER"),
                        to=[recipient_email],
                    )

                    email.send()
                    HistoriqueRappelActivite.objects.update_or_create(
                        activite=activite,
                        canal="email",
                        destinataire=recipient_email,
                        jours_avant_echeance=rule.signed_days,
                        date_echeance=activite.date,
                        defaults={
                            "objet": objet,
                            "contenu": message,
                            "statut": "sent",
                            "erreur": "",
                        },
                    )
                    rappels_envoyes += 1
                    logger.info("   Rappel envoyé avec succès")
                except Exception as e:
                    logger.error(f"   Erreur envoi email : {e}")
                    erreurs += 1
                    HistoriqueRappelActivite.objects.update_or_create(
                        activite=activite,
                        canal="email",
                        destinataire=recipient_email,
                        jours_avant_echeance=rule.signed_days,
                        date_echeance=activite.date,
                        defaults={
                            "objet": objet,
                            "contenu": message,
                            "statut": "failed",
                            "erreur": str(e),
                        },
                    )

        except Exception as e:
            erreurs += 1
            logger.error(f"Erreur traitement activité {activite.id}: {e}")
            traceback.print_exc()
            continue

    logger.info("\n" + "=" * 60)
    logger.info("FIN - Rappels d'activités")
    logger.info("Résumé :")
    logger.info(f"   - Activités traitées : {activites_traitees}")
    logger.info(f"   - Rappels envoyés : {rappels_envoyes}")
    logger.info(f"   - Doublons ignorés : {doublons_ignores}")
    logger.info("=" * 60 + "\n")

    return {
        'success': True,
        'activites_traitees': activites_traitees,
        'rappels_envoyes': rappels_envoyes,
        'doublons_ignores': doublons_ignores,
        'erreurs': erreurs,
    }
