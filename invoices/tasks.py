"""
Tâches Celery pour les relances de factures impayées
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from .models import Facture, Utilisateur, Modele_Relance, Temps_Relance

logger = logging.getLogger(__name__)


def send_invoice_reminder(facture, to_email, message_text, jours_retard):
    """
    Envoie une relance pour facture impayée

    Args:
        facture (Facture): Instance de la facture
        to_email (str): Email du fournisseur
        message_text (str): Message personnalisé
        jours_retard (int): Nombre de jours de retard

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        subject = f"Relance facture {facture.id} - Échéance dépassée"

        context = {
            'facture_id': facture.id,
            'montant': facture.montant or 0,
            'echeance': facture.echeance.strftime('%d/%m/%Y') if facture.echeance else '—',
            'jours_retard': jours_retard,
            'fournisseur': facture.fournisseur,
            'client': facture.client.nom if facture.client else '—',
        }

        try:
            message_final = message_text.format(**context)
        except KeyError:
            message_final = message_text
            logger.warning(f"Variables manquantes dans le template pour facture {facture.id}")

        print(f"\nEnvoi de l'email")
        print(f"   Sujet: {subject}")
        print(f"   Message (extrait): {message_final[:100]}...")

        email = EmailMessage(
            subject=subject,
            body=message_final,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )

        email.extra_headers = {
            'X-Invoice-Reminder': 'true',
            'X-Invoice-ID': facture.id,
            'X-Days-Overdue': str(jours_retard),
        }

        email.send()

        print(f"✅ Email envoyé avec succès à {to_email}")
        print("=" * 80 + "\n")

        return {
            'success': True,
            'message': f'Relance envoyée pour facture {facture.id}'
        }

    except Exception as e:
        print(f"\n❌ ERREUR lors de l'envoi : {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")

        return {
            'success': False,
            'message': f'Erreur : {str(e)}'
        }


@shared_task
def check_and_send_invoice_reminders():
    """
    Tâche Celery exécutée périodiquement pour vérifier et envoyer
    les relances de factures impayées
    """

    today = timezone.now().date()
    relances_envoyees = 0
    factures_traitees = 0
    erreurs = 0

    try:
        factures = Facture.objects.filter(
            statut="En cours",
            echeance__lt=timezone.now()
        ).select_related('client')

        print(f"\n📊 Nombre de factures 'En cours' avec échéance dépassée : {factures.count()}")

        for facture in factures:
            factures_traitees += 1

            try:
                if not facture.echeance:
                    print(f"Facture {facture.id} : pas de date d'échéance, ignorée")
                    continue

                date_echeance = facture.echeance.date()
                jours_retard = (today - date_echeance).days

                if jours_retard <= 0:
                    continue

                try:
                    temps_relance = Temps_Relance.objects.get(id=facture.fournisseur)
                    intervalle = temps_relance.relance
                except Temps_Relance.DoesNotExist:
                    continue

                if jours_retard % intervalle != 0:
                    continue

                print(f"\nFACTURE À RELANCER DÉTECTÉE !")
                print(f"   Facture ID: {facture.id}")
                print(f"   Fournisseur: {facture.fournisseur}")
                print(f"   Date échéance: {date_echeance}")
                print(f"   Jours de retard: {jours_retard}")
                print(f"   Intervalle: {intervalle} jours")
                print(f"   -> {jours_retard} % {intervalle} = 0 ✅")

                try:
                    utilisateur = Utilisateur.objects.get(id=facture.fournisseur)
                except Utilisateur.DoesNotExist:
                    print(f"   Utilisateur non trouvé pour fournisseur {facture.fournisseur}")
                    continue

                if not utilisateur.email:
                    print(f"   Pas d'email pour l'utilisateur {facture.fournisseur}")
                    continue

                try:
                    modele_relance = Modele_Relance.objects.get(utilisateur=facture.fournisseur)
                    message_relance = modele_relance.message
                except Modele_Relance.DoesNotExist:
                    print(f"   Pas de modèle de relance trouvé pour {facture.fournisseur}")
                    continue

                if not message_relance:
                    print(f"   Message de relance vide")
                    continue

                print(f"   Envoi de la relance...")

                result = send_invoice_reminder(
                    facture=facture,
                    to_email=utilisateur.email,
                    message_text=message_relance,
                    jours_retard=jours_retard
                )

                if result['success']:
                    print(f"   Relance envoyée avec succès !")
                    relances_envoyees += 1
                else:
                    print(f"   Échec de l'envoi : {result['message']}")
                    erreurs += 1

            except Exception as e:
                print(f"\nErreur lors du traitement de la facture {facture.id} : {e}")
                import traceback
                traceback.print_exc()
                erreurs += 1
                continue

        return {
            'success': True,
            'factures_traitees': factures_traitees,
            'relances_envoyees': relances_envoyees,
            'erreurs': erreurs
        }

    except Exception as e:
        print(f"\nERREUR CRITIQUE DANS LA TÂCHE : {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")

        return {
            'success': False,
            'message': str(e)
        }