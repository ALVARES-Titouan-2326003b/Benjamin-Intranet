"""
Tâches Celery pour les relances automatiques
"""
from celery import shared_task
from django.utils import timezone
from django_mailbox.models import Message
from .modelsadm import Utilisateur, Modele_Relance, Temps_Relance
from .email_manager import send_auto_relance
from datetime import datetime, timedelta


@shared_task
def check_and_send_auto_relances():
    """
    Tâche Celery exécutée quotidiennement pour vérifier et envoyer les relances automatiques

    Logique :
    1. Récupère tous les emails ENVOYÉS (outgoing=True)
    2. Pour chaque email, calcule : nb_jours = (aujourd'hui - date_envoi).days
    3. Si nb_jours > 0 ET nb_jours % intervalle_relance == 0 :
       → Envoyer une relance automatique avec le message personnalisé
    """
    print("\n" + "=" * 80)
    print("🤖 DÉBUT DE LA TÂCHE DE RELANCE AUTOMATIQUE")
    print(f"📅 Date d'exécution : {timezone.now()}")
    print("=" * 80)

    today = timezone.now().date()
    relances_envoyees = 0
    emails_traites = 0
    erreurs = 0

    try:
        # 1. Récupère tous les emails ENVOYÉS (outgoing=True)
        sent_emails = Message.objects.filter(outgoing=True).order_by('-processed')

        print(f"\n📊 Nombre d'emails envoyés à traiter : {sent_emails.count()}")

        for email in sent_emails:
            emails_traites += 1

            try:
                # 2. Calcule le nombre de jours depuis l'envoi
                if not email.processed:
                    print(f"⚠️  Email #{email.id} : pas de date d'envoi, ignoré")
                    continue

                date_envoi = email.processed.date()
                nb_jours = (today - date_envoi).days

                # Si l'email a été envoyé aujourd'hui, on ne relance pas
                if nb_jours <= 0:
                    continue

                # 3. Extraire l'email du destinataire depuis to_header
                destinataire_email = email.to_header

                if not destinataire_email:
                    print(f"⚠️  Email #{email.id} : pas de destinataire, ignoré")
                    continue

                # Nettoyer l'email si nécessaire (enlever le nom)
                if '<' in destinataire_email and '>' in destinataire_email:
                    destinataire_email = destinataire_email.split('<')[1].split('>')[0]

                # 4. Trouver l'utilisateur correspondant
                try:
                    utilisateur = Utilisateur.objects.get(email=destinataire_email)
                except Utilisateur.DoesNotExist:
                    # Pas d'utilisateur trouvé, on passe au suivant
                    continue

                # 5. Trouver l'intervalle de relance pour cet utilisateur
                try:
                    temps_relance = Temps_Relance.objects.get(id=utilisateur.id)
                    intervalle = temps_relance.relance
                except Temps_Relance.DoesNotExist:
                    # Pas d'intervalle de relance configuré, on passe
                    continue

                # 6. VÉRIFIER SI C'EST UN JOUR DE RELANCE
                # nb_jours doit être un multiple de l'intervalle
                if nb_jours % intervalle != 0:
                    # Ce n'est pas un jour de relance pour cet email
                    continue

                print(f"\n🎯 EMAIL À RELANCER DÉTECTÉ !")
                print(f"   Email ID: {email.id}")
                print(f"   Destinataire: {destinataire_email}")
                print(f"   Utilisateur ID: {utilisateur.id}")
                print(f"   Date envoi: {date_envoi}")
                print(f"   Jours écoulés: {nb_jours}")
                print(f"   Intervalle: {intervalle} jours")
                print(f"   → {nb_jours} % {intervalle} = 0 ✅")

                # 7. Vérifier qu'on n'a pas déjà envoyé de relance AUJOURD'HUI pour cet email
                # On cherche si un message a été envoyé aujourd'hui avec in_reply_to = cet email
                relance_deja_envoyee_aujourdhui = Message.objects.filter(
                    outgoing=True,
                    in_reply_to_id=email.id,
                    processed__date=today
                ).exists()

                if relance_deja_envoyee_aujourdhui:
                    print(f"   ⏭️  Relance déjà envoyée aujourd'hui, ignoré")
                    continue

                # 8. Récupérer le modèle de relance personnalisé
                try:
                    modele_relance = Modele_Relance.objects.get(utilisateur=utilisateur.id)
                    message_relance = modele_relance.message
                    objet_relance = modele_relance.objet
                except Modele_Relance.DoesNotExist:
                    print(f"   ⚠️  Pas de modèle de relance trouvé, ignoré")
                    continue

                if not message_relance:
                    print(f"   ⚠️  Message de relance vide, ignoré")
                    continue

                # 9. ENVOYER LA RELANCE AUTOMATIQUE
                print(f"   📮 Envoi de la relance automatique...")

                result = send_auto_relance(
                    to_email=destinataire_email,
                    subject=email.subject or "(Sans objet)",
                    message_text=message_relance,
                    objet_custom=objet_relance,
                    original_message_id=email.id
                )

                if result['success']:
                    print(f"   ✅✅✅ Relance envoyée avec succès !")
                    relances_envoyees += 1
                else:
                    print(f"   ❌ Échec de l'envoi : {result['message']}")
                    erreurs += 1

            except Exception as e:
                print(f"\n❌ Erreur lors du traitement de l'email #{email.id} : {e}")
                import traceback
                traceback.print_exc()
                erreurs += 1
                continue

        # RAPPORT FINAL
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL DE LA TÂCHE DE RELANCE")
        print("=" * 80)
        print(f"✅ Emails traités : {emails_traites}")
        print(f"📮 Relances envoyées : {relances_envoyees}")
        print(f"❌ Erreurs rencontrées : {erreurs}")
        print("=" * 80 + "\n")

        return {
            'success': True,
            'emails_traites': emails_traites,
            'relances_envoyees': relances_envoyees,
            'erreurs': erreurs
        }

    except Exception as e:
        print(f"\n❌❌❌ ERREUR CRITIQUE DANS LA TÂCHE : {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")

        return {
            'success': False,
            'message': str(e)
        }