from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from technique.models import TechnicalProject
from .email_manager import get_message_metadata
from .models import DefaultModeleRelance, ModeleRelance, Activite, TypeActivite, EmailClient
import json
from user_access.user_test_functions import has_administratif_access
import traceback
from datetime import datetime, timedelta
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
    Génère un message pré-rempli basé sur les infos de la table ModeleRelance.
    VERSION OAUTH2 : récupère les headers de l'email directement via Gmail API,
    sans dépendre de django_mailbox.

    LOGIQUE :
    1. Récupère le header "To" de l'email Gmail (= adresse du destinataire)
    2. Cherche le métier du destinataire dans EmailClient
    3. Cherche le ModeleRelance de l'utilisateur connecté pour ce métier
       → fallback sur DefaultModeleRelance si absent
    """
    try:
        data = json.loads(request.body)
        email_id = data.get('email_id')

        if not email_id:
            return JsonResponse({'success': False, 'message': 'ID email manquant'}, status=400)

        print(f"\n{'='*60}")
        print("DÉBUT generate_auto_message_view() [OAuth2]")
        print(f"   email_id: {email_id}")
        print(f"{'='*60}")

        user = request.user

        # 1. Récupère les headers de l'email via Gmail API
        try:
            from management.oauth_utils import get_gmail_service
            service = get_gmail_service(user)
            msg_data = service.users().messages().get(
                userId='me',
                id=email_id,
                format='metadata',
                metadataHeaders=['To', 'From']
            ).execute()
        except Exception as e:
            print(f"   Erreur Gmail API : {e}")
            return JsonResponse({
                'success': False,
                'message': f'Impossible de récupérer l\'email via Gmail : {str(e)}'
            }, status=502)

        headers = msg_data.get('payload', {}).get('headers', [])
        destinataire_email = next((h['value'] for h in headers if h['name'] == 'To'), None)

        if not destinataire_email:
            return JsonResponse({'success': False, 'message': 'Header "To" introuvable dans l\'email'}, status=404)

        # Nettoie le format "Prénom Nom <email@example.com>"
        import re
        match = re.search(r'<(.+?)>', destinataire_email)
        if match:
            destinataire_email = match.group(1).strip()

        print(f"   Destinataire extrait : {destinataire_email}")

        # 2. Cherche le métier du destinataire
        emails_qs = EmailClient.objects.filter(email=destinataire_email)
        if not emails_qs.exists():
            return JsonResponse({
                'success': False,
                'message': f'Client introuvable pour l\'adresse : {destinataire_email}'
            }, status=404)

        metier = emails_qs.first().metier
        print(f"   Métier trouvé : {metier}")

        # 3. Cherche le modèle de relance (personnalisé → défaut)
        try:
            message_relance = ModeleRelance.objects.get(utilisateur=user.id, metier=metier).message
            print("   ModeleRelance personnalisé trouvé")
        except ModeleRelance.DoesNotExist:
            try:
                message_relance = DefaultModeleRelance.objects.get(metier=metier).message
                print("   Fallback sur DefaultModeleRelance")
            except DefaultModeleRelance.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'Aucun modèle de relance configuré pour le métier "{metier}"'
                })

        print(f"{'='*60}\n")
        return JsonResponse({'success': True, 'message': message_relance})

    except Exception as e:
        print(f"\n ERREUR INATTENDUE : {e}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        return JsonResponse({'success': False, 'message': f'Erreur: {str(e)}'}, status=500)


@require_http_methods(["GET"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def get_calendar_activities(request):
    """
    API endpoint pour récupérer les activités du calendrier (vue MOIS).
    Retourne la référence dossier + le nom lisible du dossier.
    """
    try:
        now = datetime.now()
        month = int(request.GET.get("month", now.month))
        year = int(request.GET.get("year", now.year))

        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        activites = (
            Activite.objects
            .filter(date__gte=start_date, date__lt=end_date)
            .select_related("dossier")
            .values(
                "id",
                "dossier__reference",
                "dossier__name",
                "type",
                "date",
                "commentaire",
            )
        )

        activites_list = []
        for act in activites:
            dossier_reference = act.get("dossier__reference") or ""
            dossier_nom = act.get("dossier__name") or dossier_reference

            activites_list.append({
                "id": act["id"],
                "dossier": dossier_reference,
                "dossier_nom": dossier_nom,
                "type": act["type"] or "",
                "date": act["date"].strftime("%Y-%m-%d") if act["date"] else "",
                "commentaire": act["commentaire"] or "",
            })

        return JsonResponse({
            "success": True,
            "activites": activites_list,
            "month": month,
            "year": year,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=500)

@require_http_methods(["GET"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def get_calendar_activities_week(request):
    """
    API endpoint pour récupérer les activités d'une semaine (vue AGENDA).
    Retourne la référence dossier + le nom lisible + date/heure complètes.
    """
    try:
        date_str = request.GET.get("date")
        ref_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()

        monday = ref_date - timedelta(days=ref_date.weekday())
        sunday = monday + timedelta(days=6)

        start_dt = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
        end_dt = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59)

        activites = (
            Activite.objects
            .filter(date__gte=start_dt, date__lte=end_dt)
            .select_related("dossier")
            .values(
                "id",
                "dossier__reference",
                "dossier__name",
                "type",
                "date",
                "commentaire",
            )
        )

        activites_list = []
        for act in activites:
            dossier_reference = act.get("dossier__reference") or ""
            dossier_nom = act.get("dossier__name") or dossier_reference
            dt = act.get("date")

            activites_list.append({
                "id": act["id"],
                "dossier": dossier_reference,
                "dossier_nom": dossier_nom,
                "type": act["type"] or "",
                "date": dt.strftime("%Y-%m-%d") if dt else "",
                "time": dt.strftime("%H:%M") if dt else "09:00",
                "datetime": dt.isoformat() if dt else None,
                "commentaire": act["commentaire"] or "",
            })

        return JsonResponse({
            "success": True,
            "activites": activites_list,
            "week_start": monday.isoformat(),
            "week_end": sunday.isoformat(),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def create_activity_view(request):
    """
    API endpoint pour créer une nouvelle activité dans le calendrier

    Paramètres POST (JSON) – dossier : TextField (requis)
    — type : TextField (requis) — DOIT être en minuscule
    — date : DateTimeField (requis)
    — commentaire : TextField (optionnel)

    ATTENTION aux majuscules :
    — date_type = "Date" (avec D majuscule)
    — type = "vente" (tout en minuscule)

    Retourne — JsonResponse avec success=True/False
    """
    try:
        # Récupérer les données JSON
        data = json.loads(request.body)

        dossier = data.get('dossier', '').strip()
        type_activite = data.get('type', '').strip()
        date_str = data.get('date', '').strip()
        commentaire = data.get('commentaire', '').strip()

        print(f"\n{'=' * 60}")
        print("   Création d'activité")
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

        types_valides = ['Vente', 'Location', 'Compromis', 'Visite', 'Relance', 'Autre']
        if type_activite not in types_valides:
            return JsonResponse({
                'success': False,
                'message': f'Type invalide. Types autorisés : {", ".join(types_valides)}'
            }, status=400)

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
        type_activite = data.get('type', '').strip()
        date_str = data.get('date', '').strip()

        if not dossier or not type_activite or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'Champs obligatoires manquants'
            }, status=400)



        try:
            date_activite = datetime.fromisoformat(date_str)
            date_debut = date_activite.replace(second=0, microsecond=0)
            date_fin   = date_debut + timedelta(minutes=1)

        except ValueError as e:
            return JsonResponse({
                'success': False,
                'message': f'Format de date invalide: {e}'
            }, status=400)

        query_date = Activite.objects.filter(
            dossier=TechnicalProject.objects.get(reference=dossier),
            type=TypeActivite.objects.get(type=type_activite),
            date__gte=date_debut,
            date__lt=date_fin,
        )

        count_before = query_date.count()

        if count_before == 0:
            all_acts = Activite.objects.filter(dossier=dossier)
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