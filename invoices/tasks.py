"""
Tâches Celery pour les relances de factures impayées - VERSION AVEC DÉLAI PARAMÉTRABLE
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from .models import Facture, Fournisseur, Contact, EmailFournisseur
from management.modelsadm import GeneralModeleRelance, GeneralTempsRelance

logger = logging.getLogger(__name__)


def send_invoice_reminder(facture, to_email, message_text, jours_avant_echeance):
    """
    Envoie une relance préventive avant l'échéance de la facture
    """
    try:
        subject = f"Rappel facture {facture.id} - Échéance dans {jours_avant_echeance} jour(s)"

        clients = Contact.objects.filter(acteur=facture.client)
        nom = '-'
        for client in clients:
            if client.nom:
                nom = client.nom
                break

        context = {
            'facture_id': facture.id,
            'montant': facture.montant or 0,
            'echeance': facture.echeance.strftime('%d/%m/%Y') if facture.echeance else '—',
            'jours_avant_echeance': jours_avant_echeance,
            'fournisseur': facture.fournisseur,
            'client': nom,
        }

        try:
            message_final = message_text.format(**context)
        except KeyError:
            message_final = message_text
            logger.warning(f"Variables manquantes dans le template pour facture {facture.id}")

        email = EmailMessage(
            subject=subject,
            body=message_final,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )

        email.extra_headers = {
            'X-Invoice-Reminder': 'true',
            'X-Invoice-ID': facture.id,
            'X-Days-Before-Due': str(jours_avant_echeance),
        }

        email.send()

        return {
            'success': True,
            'message': f'Relance envoyée pour facture {facture.id}'
        }

    except Exception as e:
        print(f"\nERREUR lors de l'envoi : {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")

        return {
            'success': False,
            'message': f'Erreur : {str(e)}'
        }


@shared_task
def check_and_send_invoice_reminders(delai_relance=None):
    """
    Tâche Celery - Vérification et envoi des rappels préventifs

    Args:
        delai_relance (int, optional): Si fourni, met à jour TOUS les délais
                                       dans Temps_Relance avant la vérification.
                                       Si None, utilise les délais existants.

    LOGIQUE : Relance à J-X (X = intervalle configuré dans Temps_Relance)
    """

    today = timezone.now().date()

    # ÉTAPE 1 : Mise à jour du délai si fourni
    if delai_relance is not None:
        try:
            nb_lignes_avant = Temps_Relance.objects.count()

            if nb_lignes_avant == 0:
                return {
                    'success': False,
                    'message': 'Aucune configuration trouvée dans Temps_Relance'
                }

            # UPDATE de toutes les lignes
            GeneralTempsRelance.objects.all().update(temps=delai_relance)

        except Exception as e:
            print(f"\nERREUR lors de la mise à jour de GeneralTempsRelance : {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erreur lors de la mise à jour des délais : {str(e)}'
            }

    # ÉTAPE 2 : Vérification et envoi des relances
    relances_envoyees = 0
    factures_traitees = 0
    erreurs = 0

    try:
        factures = Facture.objects.filter(
            statut="En cours",
            echeance__gt=timezone.now()
        ).select_related('client')

        # Récupérer intervalle
        try:
            intervalle = GeneralTempsRelance.objects.all().first().temps
        except Temps_Relance.DoesNotExist:
            return {
                'success': False,
                'message': "IGNORÉE : Pas de GeneralTempsRelance"
            }

        for facture in factures:
            factures_traitees += 1

            try:
                # Vérifier échéance
                if not facture.echeance:
                    continue

                # Calculer jours avant échéance
                jours_avant_echeance = (facture.echeance.date() - today).days

                if jours_avant_echeance <= 0:
                    continue

                # Vérifier si c'est le bon jour
                if jours_avant_echeance != intervalle:
                    continue

                # Récupérer l'adresse
                try:
                    fournisseur = Fournisseur.objects.get(id=facture.fournisseur)
                    contacts = Contact.objects.filter(acteur=facture.fournisseur)
                    adresse = ""

                    for contact in contacts:
                        email = EmailFournisseur.object.filter(contact=contact.id).first()
                        if email and email.email:
                            adresse = email.email
                            break

                except Fournisseur.DoesNotExist:
                    continue

                if not adresse:
                    continue

                # Récupérer modèle de relance
                try:
                    message_relance = GeneralModeleRelance.objects.all().first().message
                except GeneralModeleRelance.DoesNotExist:
                    continue

                if not message_relance:
                    continue

                # ENVOYER LA RELANCE
                result = send_invoice_reminder(
                    facture=facture,
                    to_email=adresse,
                    message_text=message_relance,
                    jours_avant_echeance=jours_avant_echeance
                )

                if result['success']:
                    relances_envoyees += 1
                else:
                    erreurs += 1

            except Exception as e:
                import traceback
                traceback.print_exc()
                erreurs += 1
                continue

        return {
            'success': True,
            'factures_traitees': factures_traitees,
            'relances_envoyees': relances_envoyees,
            'erreurs': erreurs,
            'delai_applique': delai_relance
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e)
        }