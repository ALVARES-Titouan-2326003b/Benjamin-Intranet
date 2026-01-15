"""
Tâches Celery pour les relances de factures impayées - VERSION AVEC DÉLAI PARAMÉTRABLE
"""
from celery import shared_task
from django.urls import reverse
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from .models import Facture, Utilisateur, Modele_Relance, Temps_Relance

logger = logging.getLogger(__name__)


def send_invoice_reminder(facture, to_email, message_text, jours_avant_echeance):
    """
    Envoie une relance préventive avant l'échéance de la facture
    """
    try:
        subject = f"Rappel facture {facture.id} - Échéance dans {jours_avant_echeance} jour(s)"

        context = {
            'facture_id': facture.id,
            'montant': facture.montant or 0,
            'echeance': facture.echeance.strftime('%d/%m/%Y') if facture.echeance else '—',
            'jours_avant_echeance': jours_avant_echeance,
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
            'X-Days-Before-Due': str(jours_avant_echeance),
        }

        email.send()

        print(f"Email envoyé avec succès à {to_email}")
        print("=" * 80 + "\n")

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
    print("\n" + "=" * 80)
    print("DÉBUT DE LA TÂCHE DE RAPPEL PRÉVENTIF FACTURES")
    print(f"Date d'exécution : {timezone.now()}")
    print("=" * 80)

    today = timezone.now().date()
    print(f"today = {today}")

    # ============================================================
    # ÉTAPE 1 : Mise à jour du délai si fourni
    # ============================================================
    if delai_relance is not None:
        try:
            print(f"\n{'='*80}")
            print(f"MISE À JOUR DES DÉLAIS DE RELANCE")
            print(f"{'='*80}")
            print(f"Délai demandé : {delai_relance} jour(s)")

            nb_lignes_avant = Temps_Relance.objects.count()
            print(f"📊 Nombre de lignes dans Temps_Relance : {nb_lignes_avant}")

            if nb_lignes_avant == 0:
                print("⚠ATTENTION : Aucune ligne dans Temps_Relance !")
                print("=" * 80 + "\n")
                return {
                    'success': False,
                    'message': 'Aucune configuration trouvée dans Temps_Relance'
                }

            # UPDATE de toutes les lignes
            nb_lignes_mises_a_jour = Temps_Relance.objects.all().update(relance=delai_relance)

            print(f"{nb_lignes_mises_a_jour} ligne(s) mise(s) à jour avec relance = {delai_relance}")
            print(f"{'='*80}\n")

        except Exception as e:
            print(f"\nERREUR lors de la mise à jour de Temps_Relance : {e}")
            import traceback
            traceback.print_exc()
            print("=" * 80 + "\n")
            return {
                'success': False,
                'message': f'Erreur lors de la mise à jour des délais : {str(e)}'
            }
    else:
        print(f"\nAucun délai spécifié, utilisation des délais existants dans Temps_Relance\n")

    # ============================================================
    # ÉTAPE 2 : Vérification et envoi des relances
    # ============================================================
    relances_envoyees = 0
    factures_traitees = 0
    erreurs = 0

    try:
        factures = Facture.objects.filter(
            statut="En cours",
            echeance__gt=timezone.now()
        ).select_related('client')

        print(f"Nombre de factures 'En cours' avec échéance à venir : {factures.count()}\n")

        for facture in factures:
            factures_traitees += 1

            print(f"{'='*60}")
            print(f"TRAITEMENT FACTURE #{factures_traitees} : {facture.id}")
            print(f"{'='*60}")

            try:
                # Vérifier échéance
                if not facture.echeance:
                    print(f"IGNORÉE : Pas de date d'échéance")
                    continue

                date_echeance = facture.echeance.date()
                print(f"Date échéance : {date_echeance}")

                # Calculer jours avant échéance
                jours_avant_echeance = (date_echeance - today).days
                print(f"Jours avant échéance : {jours_avant_echeance}")

                if jours_avant_echeance <= 0:
                    print(f"IGNORÉE : Échéance déjà passée ou aujourd'hui")
                    continue

                print(f"Échéance future OK")

                # Récupérer intervalle
                print(f"Recherche Temps_Relance pour fournisseur : {facture.fournisseur}")
                try:
                    temps_relance = Temps_Relance.objects.get(id=facture.fournisseur)
                    intervalle = temps_relance.relance
                    print(f"Intervalle trouvé : {intervalle} jours")
                except Temps_Relance.DoesNotExist:
                    print(f"IGNORÉE : Pas de Temps_Relance pour fournisseur {facture.fournisseur}")
                    continue

                # Vérifier si c'est le bon jour
                print(f"Vérification : {jours_avant_echeance} == {intervalle} ?")
                if jours_avant_echeance != intervalle:
                    print(f"IGNORÉE : Ce n'est pas le jour de relance ({jours_avant_echeance} != {intervalle})")
                    continue

                print(f"C'EST LE BON JOUR POUR RELANCER !")

                # Récupérer collaborateur assigné
                if not facture.collaborateur:
                    print(f"IGNORÉE : Pas de collaborateur assigné à la facture")
                    continue

                to_email = facture.collaborateur.email
                if not to_email:
                    print(f"IGNORÉE : Le collaborateur {facture.collaborateur} n'a pas d'adresse email")
                    continue

                print(f"Collaborateur trouvé : {facture.collaborateur} ({to_email})")

                # Construction du lien et du message
                try:
                    url_facture = f"{settings.SITE_URL.rstrip('/')}{reverse('invoices:detail', args=[facture.id])}"
                except Exception as e:
                    print(f"Erreur construction URL: {e}")
                    url_facture = "#"

                message_relance = (
                    f"Bonjour,\n\n"
                    f"Vous avez une facture en attente (Facture n°{facture.id}).\n\n"
                    f"Vous pouvez la consulter en cliquant sur ce lien :\n{url_facture}\n\n"
                    f"Cordialement,\n"
                    f"L'équipe Benjamin Intranet"
                )
                print(f"Message généré avec lien : {url_facture}")

                # ENVOYER LA RELANCE
                print(f"\nENVOI DE LA RELANCE...")

                result = send_invoice_reminder(
                    facture=facture,
                    to_email=to_email,
                    message_text=message_relance,
                    jours_avant_echeance=jours_avant_echeance
                )

                if result['success']:
                    print(f"RELANCE ENVOYÉE AVEC SUCCÈS !")
                    relances_envoyees += 1
                else:
                    print(f"Échec de l'envoi : {result['message']}")
                    erreurs += 1

            except Exception as e:
                print(f"\nERREUR lors du traitement : {e}")
                import traceback
                traceback.print_exc()
                erreurs += 1
                continue

        # RAPPORT FINAL
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL DE LA TÂCHE DE RAPPEL PRÉVENTIF")
        print("=" * 80)
        print(f"Factures traitées : {factures_traitees}")
        print(f" Relances envoyées : {relances_envoyees}")
        print(f"Erreurs rencontrées : {erreurs}")
        if delai_relance is not None:
            print(f"Délai appliqué : {delai_relance} jour(s)")
        print("=" * 80 + "\n")

        return {
            'success': True,
            'factures_traitees': factures_traitees,
            'relances_envoyees': relances_envoyees,
            'erreurs': erreurs,
            'delai_applique': delai_relance
        }

    except Exception as e:
        print(f"\n❌❌❌ ERREUR CRITIQUE : {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e)
        }