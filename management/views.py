"""
Vues pour la partie administrative - Gestion des emails et relances
VERSION OAUTH2 : Passe request.user aux fonctions email_manager
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from technique.models import TechnicalProject
from .email_manager import fetch_new_emails, get_sent_emails, get_email_summary, send_email_reply
from .models import DefaultModeleRelance, ModeleRelance, Activite, TypeActivite
import json
from user_access.user_test_functions import has_administratif_access
from celery import Celery
import traceback
from datetime import datetime
from django.contrib.auth import get_user_model

Utilisateur = get_user_model()


@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def administratif_view(request):

    """
    Page du pôle administratif - LOGIQUE INVERSÉE : affiche les emails ENVOYÉS
    VERSION OAUTH2 : Récupère les emails de l'utilisateur connecté
    """

    user = request.user
    fetch_new_emails(user)
    emails = get_sent_emails(user, limit=20)
    emails_data = [get_email_summary(email) for email in emails]

    dossiers = TechnicalProject.objects.all().order_by('reference')
    types = TypeActivite.objects.distinct()

    return render(request, 'management.html', {
        'pole_name': 'Administratif',
        'emails': emails_data,
        'dossiers': dossiers,
        'types': types
    })


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def send_reply_view(request):
    """
    API endpoint pour envoyer une relance à un destinataire
    VERSION OAUTH2 : N'utilise plus Message.objects car les IDs sont des IDs Gmail (strings)
    Retourne une réponse JSON
    """
    try:
        data = json.loads(request.body)

        email_id = data.get('email_id')
        message_text = data.get('message')
        to_email = data.get('to_email')
        subject = data.get('subject')

        if not email_id or not message_text:
            return JsonResponse({
                'success': False,
                'message': 'Données manquantes'
            }, status=400)

        if not to_email or not subject:
            return JsonResponse({
                'success': False,
                'message': 'Destinataire ou sujet manquant'
            }, status=400)

        user = request.user

        result = send_email_reply(
            to_email=to_email,
            subject=subject,
            message_text=message_text,
            original_message_id=email_id,
            user=user
        )

        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def generate_auto_message_view(request):
    """
    Génère un message pré-rempli basé sur les infos de la table ModeleRelance
    INCHANGÉ : Ne nécessite pas de modification pour OAuth2

    LOGIQUE DE LIAISON :
    1. Email.to_header → Utilisateur.email
    2. Utilisateur.id → ModeleRelance.utilisateur

    Structure des tables :
    - Utilisateurs : id (PK), email, nom, prenom
    - ModeleRelance : utilisateur (PK, FK → Utilisateurs.id), message, objet

    Returns:
        JsonResponse: {'success': bool, 'message': str}
    """
    try:
        data = json.loads(request.body)
        email_id = data.get('email_id')

        if not email_id:
            return JsonResponse({
                'success': False,
                'message': 'ID email manquant'
            }, status=400)

        print(f"\n{'='*60}")
        print(f"DÉBUT generate_auto_message_view()")
        print(f"   email_id: {email_id}")
        print(f"{'='*60}")

        from django_mailbox.models import Message
        original_email = Message.objects.filter(message_id=email_id).first()
        if original_email is None:
            return JsonResponse({
                'success': False,
                'message': 'Email introuvable'
            })

        destinataire_email = original_email.to_header

        emails = EmailClient.objects.filter(email=destinataire_email)

        if emails.count() == 0:
            return JsonResponse({
                'success': False,
                'message': 'Client introuvable'
            }, status=404)

        metier = emails.first().metier

        try:
            user = Utilisateur.objects.get(email=original_email.from_header)
        except Utilisateur.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur introuvable'
            }, status=404)

        # 4. Récupère le modèle de message
        try:
            message_relance = ModeleRelance.objects.get(utilisateur=user.id, metier=metier).message
        except ModeleRelance.DoesNotExist:
            try:
                message_relance = DefaultModeleRelance.objects.get(metier=metier).message
            except DefaultModeleRelance.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f"Pas de DefaultModeleRelance pour le métier {metier}"
                })

        # 5. Construit la réponse JSON
        response_data = {
            'success': True,
            'message': message_relance
        }

        return JsonResponse(response_data)

    except Exception as e:
        print(f"\n ERREUR INATTENDUE : {e}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def get_calendar_activities(request):
    """
    API endpoint pour récupérer les activités du calendrier
    INCHANGÉ : Ne nécessite pas de modification pour OAuth2

    Paramètres GET :
    - month : numéro du mois (1-12)
    - year : année (ex: 2025)

    Retourne :
    - Liste des activités avec leurs détails pour affichage dans le calendrier
    """
    try:
        now = datetime.now()
        month = int(request.GET.get('month', now.month))
        year = int(request.GET.get('year', now.year))

        print(f"\n{'=' * 60}")
        print(f" API Calendar Activities - Requête pour {month}/{year}")
        print(f"{'=' * 60}")

        start_date = datetime(year, month, 1)

        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        print(f" Période : {start_date.date()} → {end_date.date()}")

        activites = Activite.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).values('id', 'dossier', 'type', 'date', 'commentaire')

        print(f" Activités trouvées : {activites.count()}")

        activites_list = []
        for act in activites:
            activites_list.append({
                'id': act['id'],
                'dossier': act['dossier'],
                'type': act['type'],
                'date': act['date'].strftime('%Y-%m-%d'),
                'commentaire': act['commentaire'] or ''
            })
            print(f"   - {act['date'].strftime('%Y-%m-%d')} : {act['type']} - {act['dossier']}")

        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': True,
            'activites': activites_list,
            'month': month,
            'year': year
        })

    except Exception as e:
        print(f"\n Erreur API Calendar Activities : {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def create_activity_view(request):
    """
    API endpoint pour créer une nouvelle activité dans le calendrier

    Paramètres POST (JSON) :
    - dossier : TextField (requis)
    - type : TextField (requis) - DOIT être en minuscule
    - date : DateTimeField (requis)
    - commentaire : TextField (optionnel)

    ATTENTION aux majuscules :
    - date_type = "Date" (avec D majuscule)
    - type = "vente" (tout en minuscule)

    Retourne :
    - JsonResponse avec success=True/False
    """
    try:
        # Récupérer les données JSON
        data = json.loads(request.body)

        dossier = data.get('dossier', '').strip()
        type_activite = data.get('type', '').strip().lower()
        date_str = data.get('date', '').strip()
        commentaire = data.get('commentaire', '').strip()

        print(f"\n{'=' * 60}")
        print(f"   Création d'activité")
        print(f"   Dossier: {dossier}")
        print(f"   Type: {type_activite}")
        print(f"   Date: {date_str}")
        print(f"   Commentaire: {commentaire[:50] if commentaire else '(vide)'}")
        print(f"{'=' * 60}")

        if not dossier or not type_activite or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'Champs obligatoires manquants'
            }, status=400)

        types_valides = ['vente', 'location', 'compromis', 'visite', 'relance', 'autre']
        if type_activite not in types_valides:
            return JsonResponse({
                'success': False,
                'message': f'Type invalide. Types autorisés : {", ".join(types_valides)}'
            }, status=400)

        from datetime import datetime
        try:
            date_activite = datetime.fromisoformat(date_str)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Format de date invalide'
            }, status=400)

        from django.db.models import Max
        max_id_result = Activite.objects.aggregate(Max('id'))['id__max']

        if max_id_result is None:
            next_id = 1
        else:
            try:
                max_id_int = int(max_id_result)
                next_id = max_id_int + 1
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': f'Type d\'ID invalide dans la BD : {type(max_id_result)}'
                }, status=500)

        print(f"   Max ID actuel: {max_id_result}")
        print(f"   Prochain ID: {next_id}")

        nouvelle_activite = Activite.objects.create(
            id=next_id,
            dossier=TechnicalProject.objects.get(reference=dossier),
            type=TypeActivite.objects.get(type=type_activite),
            date=date_activite,
            date_type='Date',
            commentaire=commentaire if commentaire else None
        )

        print(f"   Activité créée avec succès (ID: {nouvelle_activite.id})")
        print(f"   └─ Type: '{nouvelle_activite.type}'")
        print(f"   └─ Date_type: '{nouvelle_activite.date_type}'")
        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': True,
            'message': 'Activité créée avec succès',
            'activity_id': nouvelle_activite.id
        })

    except Exception as e:
        print(f"\n Erreur création activité : {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def delete_activity_view(request):
    """
    API endpoint pour supprimer une ou plusieurs activités correspondant aux critères
    """
    try:
        data = json.loads(request.body)

        dossier = data.get('dossier', '').strip()
        type_activite = data.get('type', '').strip().lower()
        date_str = data.get('date', '').strip()

        if not dossier or not type_activite or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'Champs obligatoires manquants'
            }, status=400)



        try:
            date_activite = datetime.fromisoformat(date_str)
            date_debut = date_activite.replace(second=0, microsecond=0)


        except ValueError as e:
            return JsonResponse({
                'success': False,
                'message': f'Format de date invalide: {e}'
            }, status=400)

        query_date = Activite.objects.filter(
            dossier=TechnicalProject.objects.get(reference=dossier),
            type=TypeActivite.objects.get(type=type_activite),
            date__gte=date_debut,
        )

        count_before = query_date.count()

        if count_before == 0:
            all_acts = Activites.objects.filter(dossier=dossier)
            for act in all_acts:
                print(f"      ID {act.id}: {act.date} | type={act.type}")

            return JsonResponse({
                'success': False,
                'message': 'Aucune activité ne correspond à ces critères'
            }, status=404)

        deleted_count, _ = query_date.delete()

        print(f"   {deleted_count} activité(s) supprimée(s)")

        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} activité(s) supprimée(s) avec succès',
            'deleted_count': deleted_count
        })

    except Exception as e:
        print(f"\n Erreur suppression: {e}")
        import traceback
        traceback.print_exc()

        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)