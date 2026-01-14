"""
VERSION DEBUG ULTRA-DETAILLE
VERSION MICROSOFT GRAPH API
Cette version affiche EXACTEMENT ou chaque email est bloque
"""
import os
from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from .modelsadm import Utilisateur, Modele_Relance, Temps_Relance, Activites, OAuthToken
from .email_manager import send_auto_relance, get_sent_emails_for_celery
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_and_send_auto_relances():
    """
    VERSION DEBUG ULTRA-DETAILLE
    VERSION MICROSOFT GRAPH API
    """
    print("\n" + "=" * 80)
    print("VERSION DEBUG ULTRA-DETAILLE - MICROSOFT GRAPH API")
    print(f"Date d'execution : {timezone.now()}")
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
            print("\nAucun utilisateur avec token OAuth trouve")
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
                # CHANGEMENT MICROSOFT : get_sent_emails_for_celery vient de email_manager.py
                sent_emails = get_sent_emails_for_celery(user, limit=100)

                print(f"   {len(sent_emails)} emails trouves dans SENT")

                pending_count = sum(1 for e in sent_emails if e.get('status') == 'pending')
                replied_count = sum(1 for e in sent_emails if e.get('status') == 'replied')
                print(f"   └─ {pending_count} en attente, {replied_count} repondus")

                # DEBUG : Afficher les details de chaque email
                print(f"\n   ANALYSE DETAILLEE DE CHAQUE EMAIL:")
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
                            print(f"         BLOQUE : Email deja repondu")
                            blocked_at['status_replied'] += 1
                            continue

                        # CHECK 2 : Date
                        date_envoi = email_data.get('date')
                        if not date_envoi:
                            print(f"         BLOQUE : Pas de date d'envoi")
                            blocked_at['date_missing'] += 1
                            continue

                        if hasattr(date_envoi, 'date'):
                            date_envoi = date_envoi.date()

                        nb_jours = (today - date_envoi).days
                        print(f"      └─ Date envoi: {date_envoi}")
                        print(f"      └─ Jours ecoules: {nb_jours}")

                        print(f"      └─ Test: nb_jours < 0 ? {nb_jours < 0}")
                        if nb_jours < 1:
                            print(f"         BLOQUE : nb_jours < 1")
                            blocked_at['nb_jours_check'] += 1
                            continue

                        print(f"      └─ Passe le check nb_jours")

                        destinataire_email = email_data.get('to', '')

                        if not destinataire_email:
                            print(f"         BLOQUE : Pas de destinataire")
                            blocked_at['email_missing'] += 1
                            continue

                        if '<' in destinataire_email and '>' in destinataire_email:
                            destinataire_email = destinataire_email.split('<')[1].split('>')[0].strip()

                        print(f"      └─ Destinataire nettoye: {destinataire_email}")

                        try:
                            utilisateur = Utilisateur.objects.get(email=destinataire_email)
                            print(f"      └─ Utilisateur trouve: {utilisateur.nom} (ID: {utilisateur.id})")
                        except Utilisateur.DoesNotExist:
                            print(f"         BLOQUE : Utilisateur '{destinataire_email}' pas dans table Utilisateur")
                            blocked_at['utilisateur_not_found'] += 1
                            continue

                        try:
                            temps_relance = Temps_Relance.objects.get(id=utilisateur.id)
                            intervalle = temps_relance.relance
                            print(f"      └─ Intervalle de relance: {intervalle} jours")
                        except Temps_Relance.DoesNotExist:
                            print(f"         BLOQUE : Pas de Temps_Relance pour utilisateur ID {utilisateur.id}")
                            blocked_at['temps_relance_not_found'] += 1
                            continue

                        if nb_jours % intervalle != 0:
                            print(f"         BLOQUE : {nb_jours} n'est pas un multiple de {intervalle}")
                            blocked_at['modulo_check'] += 1
                            continue

                        print(f"      └─ Passe le check modulo")

                        try:
                            modele_relance = Modele_Relance.objects.get(utilisateur=utilisateur.id)
                            message_relance = modele_relance.message
                            objet_relance = modele_relance.objet
                            print(f"      └─ Modele de relance trouve")
                            print(f"         Objet: {objet_relance[:30] if objet_relance else 'N/A'}...")
                        except Modele_Relance.DoesNotExist:
                            print(f"         BLOQUE : Pas de Modele_Relance pour utilisateur ID {utilisateur.id}")
                            blocked_at['modele_relance_not_found'] += 1
                            continue

                        # CHECK 9 : Message vide
                        if not message_relance:
                            print(f"         BLOQUE : Message de relance vide")
                            blocked_at['message_empty'] += 1
                            continue

                        print(f"      └─ Message: {message_relance[:50]}...")

                        print(f"\n      TOUS LES CHECKS PASSES ! ENVOI EN COURS...")

                        result = send_auto_relance(
                            to_email=destinataire_email,
                            subject=email_data.get('subject', '(Sans objet)'),
                            message_text=message_relance,
                            objet_custom=objet_relance,
                            original_message_id=email_data.get('id'),
                            user=user
                        )

                        if result['success']:
                            print(f"         RELANCE ENVOYEE !")
                            blocked_at['sent_successfully'] += 1
                            relances_envoyees += 1
                        else:
                            print(f"         ECHEC ENVOI : {result['message']}")
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
        print(f"RÉSUMÉ DE L'EXÉCUTION")
        print("=" * 80)
        print(f"📊 Statistiques globales :")
        print(f"   ├─ Emails traites : {emails_traites}")
        print(f"   ├─ Relances envoyees : {relances_envoyees}")
        print(f"   └─ Erreurs : {erreurs}")
        print(f"\n📋 Détail des blocages :")
        print(f"   ├─ Emails repondus (status != pending) : {blocked_at['status_replied']}")
        print(f"   ├─ Date manquante : {blocked_at['date_missing']}")
        print(f"   ├─ Bloque par 'nb_jours < 1' : {blocked_at['nb_jours_check']}")
        print(f"   ├─ Email destinataire manquant : {blocked_at['email_missing']}")
        print(f"   ├─ Utilisateur pas dans BD : {blocked_at['utilisateur_not_found']}")
        print(f"   ├─ Temps_Relance pas trouve : {blocked_at['temps_relance_not_found']}")
        print(f"   ├─ Bloque par modulo (nb_jours % intervalle) : {blocked_at['modulo_check']}")
        print(f"   ├─ Modele_Relance pas trouve : {blocked_at['modele_relance_not_found']}")
        print(f"   ├─ Message de relance vide : {blocked_at['message_empty']}")
        print(f"   ├─ Relances envoyees avec succes : {blocked_at['sent_successfully']}")
        print(f"   └─ Echecs d'envoi : {blocked_at['send_failed']}")
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


@shared_task
def check_and_send_activite_reminders():
    """
    Tache periodique qui verifie les activites a venir
    et envoie des rappels 10, 7, 4 et 1 jour(s) avant la date prevue
    INCHANGE : Ne necessite pas de modification pour Microsoft Graph
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEBUT - Verification des rappels d'activites")
    logger.info("=" * 60)

    now = datetime.now()
    today = now.date()
    logger.info(f"Date actuelle : {today}")

    # Date limite : dans 10 jours
    date_limite = today + timedelta(days=10)
    logger.info(f"Date limite : {date_limite} (dans 10 jours)")

    # Recuperer toutes les activites dans les 10 prochains jours
    activites = Activites.objects.filter(
        date__date__gt=today,
        date__date__lte=date_limite
    ).order_by('date')

    logger.info(f"Activites trouvees dans les 10 prochains jours : {activites.count()}")

    activites_traitees = 0
    rappels_envoyes = 0

    for activite in activites:
        try:
            activites_traitees += 1

            date_activite = activite.date.date()
            jours_restants = (date_activite - today).days

            logger.info(f"\nActivite #{activite.id}")
            logger.info(f"   Dossier: {activite.dossier}")
            logger.info(f"   Type: {activite.type}")
            logger.info(f"   Date: {date_activite}")
            logger.info(f"   Jours restants: {jours_restants}")

            should_send = False

            if jours_restants in [1, 4, 7, 10]:
                should_send = True
                logger.info(f"   Rappel necessaire (J-{jours_restants})")
            else:
                logger.info(f"   Pas de rappel pour J-{jours_restants}")

            if should_send:
                # Construire le message
                objet = f"Rappel d'activite - J-{jours_restants}"

                message = f"""Bonjour,

Ceci est un rappel automatique concernant l'activite suivante :

- Dossier : {activite.dossier}
- Type : {activite.type}
- Date prevue : {date_activite.strftime('%d/%m/%Y')}
- Echeance : dans {jours_restants} jour(s)

"""

                if activite.commentaire:
                    message += f"Commentaire : {activite.commentaire}\n\n"

                message += f"""Merci de prendre les dispositions necessaires.

Cordialement,
Systeme de rappel Benjamin Immobilier"""

                # Envoyer l'email a l'administrateur
                try:
                    email = EmailMessage(
                        subject=objet,
                        body=message,
                        from_email=os.getenv("EMAIL_HOST_USER"),
                        to=[os.getenv("EMAIL_HOST_USER")],
                    )

                    email.send()
                    rappels_envoyes += 1
                    logger.info(f"   Rappel envoye avec succes")
                except Exception as e:
                    logger.error(f"   Erreur envoi email : {e}")

        except Exception as e:
            logger.error(f"Erreur traitement activite {activite.id}: {e}")
            import traceback
            traceback.print_exc()
            continue

    logger.info("\n" + "=" * 60)
    logger.info(f"FIN - Rappels d'activites")
    logger.info(f"Resume :")
    logger.info(f"   - Activites traitees : {activites_traitees}")
    logger.info(f"   - Rappels envoyes : {rappels_envoyes}")
    logger.info("=" * 60 + "\n")

    return {
        'success': True,
        'activites_traitees': activites_traitees,
        'rappels_envoyes': rappels_envoyes
    }