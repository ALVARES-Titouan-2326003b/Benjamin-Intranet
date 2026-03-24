import json
import traceback
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from technique.models import TechnicalProject
from user_access.user_test_functions import has_administratif_access

from .email_manager import (
    fetch_new_emails,
    get_email_summary,
    get_message_metadata,
    get_sent_emails,
    send_email_reply,
)
from .models import (
    Activite,
    DefaultModeleRelance,
    EmailClient,
    ModeleRelance,
    TypeActivite,
)


def _json_error(message, status=400):
    return JsonResponse({"success": False, "message": message}, status=status)


def _parse_request_json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        raise ValueError("JSON invalide")


def _parse_iso_datetime(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("Date manquante")

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def administratif_view(request):
    """
    Page du pôle administratif.
    Affiche les emails envoyés depuis Outlook/Microsoft Graph.
    """
    user = request.user

    fetch_new_emails(user)
    emails = get_sent_emails(user, limit=20)
    emails_data = [get_email_summary(email) for email in emails]

    dossiers = TechnicalProject.objects.all().order_by("reference")
    types = TypeActivite.objects.all().order_by("type")

    return render(
        request,
        "management.html",
        {
            "pole_name": "Administratif",
            "emails": emails_data,
            "dossiers": dossiers,
            "types": types,
        },
    )


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def send_reply_view(request):
    """
    Envoie une relance / réponse sur un email Outlook.
    Si original_message_id est fourni, la réponse part dans le thread existant.
    """
    try:
        data = _parse_request_json(request)

        email_id = (data.get("email_id") or "").strip()
        message_text = (data.get("message") or "").strip()
        to_email = (data.get("to_email") or "").strip()
        subject = (data.get("subject") or "").strip()

        if not email_id:
            return _json_error("ID email manquant")

        if not message_text:
            return _json_error("Message manquant")

        result = send_email_reply(
            user=request.user,
            original_message_id=email_id,
            message_text=message_text,
            subject=subject,
            to_email=to_email,
        )

        return JsonResponse(result, status=200 if result.get("success") else 400)

    except ValueError as e:
        return _json_error(str(e))
    except Exception as e:
        traceback.print_exc()
        return _json_error(f"Erreur : {str(e)}", status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def generate_auto_message_view(request):
    try:
        data = json.loads(request.body)
        email_id = data.get('email_id')

        if not email_id:
            return JsonResponse({'success': False, 'message': 'ID email manquant'}, status=400)

        # Récupérer les métadonnées du message via Graph API
        from management.email_manager import get_message_metadata
        msg_meta = get_message_metadata(request.user, email_id)

        if not msg_meta:
            return JsonResponse({'success': False, 'message': 'Email introuvable via Graph API'})

        # Extraire l'adresse du destinataire original
        to_recipients = msg_meta.get('toRecipients', [])
        destinataire_email = (
            to_recipients[0].get('emailAddress', {}).get('address', '')
            if to_recipients else ''
        )

        if not destinataire_email:
            return JsonResponse({'success': False, 'message': 'Destinataire introuvable'})

        # Chercher le modèle de relance via l'email client
        from management.models import EmailClient, ModeleRelance, DefaultModeleRelance
        emails = EmailClient.objects.filter(email=destinataire_email)

        if not emails.exists():
            return JsonResponse({'success': False, 'message': 'Client introuvable'})

        metier = emails.first().metier

        try:
            message_relance = ModeleRelance.objects.get(
                utilisateur=request.user.id, metier=metier
            ).message
        except ModeleRelance.DoesNotExist:
            try:
                message_relance = DefaultModeleRelance.objects.get(metier=metier).message
            except DefaultModeleRelance.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'Pas de modèle de relance pour le métier {metier}'
                })

        return JsonResponse({'success': True, 'message': message_relance})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'Erreur: {str(e)}'}, status=500)


@require_http_methods(["GET"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def get_calendar_activities(request):
    """
    Récupère les activités du calendrier pour une vue mensuelle.
    """
    try:
        now = datetime.now()
        month = int(request.GET.get("month", now.month))
        year = int(request.GET.get("year", now.year))

        start_date = datetime(year, month, 1)
        end_date = (
            datetime(year + 1, 1, 1)
            if month == 12
            else datetime(year, month + 1, 1)
        )

        activites = (
            Activite.objects.filter(date__gte=start_date, date__lt=end_date)
            .select_related("dossier", "type")
            .values(
                "id",
                "dossier__reference",
                "dossier__name",
                "type__type",
                "date",
                "commentaire",
            )
            .order_by("date", "id")
        )

        activites_list = []
        for act in activites:
            dossier_reference = act.get("dossier__reference") or ""
            dossier_nom = act.get("dossier__name") or dossier_reference

            activites_list.append(
                {
                    "id": act["id"],
                    "dossier": dossier_reference,
                    "dossier_nom": dossier_nom,
                    "type": act.get("type__type") or "",
                    "date": act["date"].strftime("%Y-%m-%d") if act["date"] else "",
                    "commentaire": act.get("commentaire") or "",
                }
            )

        return JsonResponse(
            {
                "success": True,
                "activites": activites_list,
                "month": month,
                "year": year,
            }
        )

    except ValueError as e:
        return _json_error(f"Paramètre invalide : {str(e)}")
    except Exception as e:
        traceback.print_exc()
        return _json_error(str(e), status=500)


@require_http_methods(["GET"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def get_calendar_activities_week(request):
    """
    Récupère les activités d'une semaine (vue agenda).
    """
    try:
        date_str = request.GET.get("date")
        ref_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else datetime.now().date()
        )

        monday = ref_date - timedelta(days=ref_date.weekday())
        sunday = monday + timedelta(days=6)

        start_dt = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
        end_dt = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59)

        activites = (
            Activite.objects.filter(date__gte=start_dt, date__lte=end_dt)
            .select_related("dossier", "type")
            .values(
                "id",
                "dossier__reference",
                "dossier__name",
                "type__type",
                "date",
                "commentaire",
            )
            .order_by("date", "id")
        )

        activites_list = []
        for act in activites:
            dossier_reference = act.get("dossier__reference") or ""
            dossier_nom = act.get("dossier__name") or dossier_reference
            dt = act.get("date")

            activites_list.append(
                {
                    "id": act["id"],
                    "dossier": dossier_reference,
                    "dossier_nom": dossier_nom,
                    "type": act.get("type__type") or "",
                    "date": dt.strftime("%Y-%m-%d") if dt else "",
                    "time": dt.strftime("%H:%M") if dt else "09:00",
                    "datetime": dt.isoformat() if dt else None,
                    "commentaire": act.get("commentaire") or "",
                }
            )

        return JsonResponse(
            {
                "success": True,
                "activites": activites_list,
                "week_start": monday.isoformat(),
                "week_end": sunday.isoformat(),
            }
        )

    except ValueError as e:
        return _json_error(f"Date invalide : {str(e)}")
    except Exception as e:
        traceback.print_exc()
        return _json_error(str(e), status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def create_activity_view(request):
    """
    Crée une nouvelle activité dans le calendrier.
    """
    try:
        data = _parse_request_json(request)

        dossier_ref = (data.get("dossier") or "").strip()
        type_label = (data.get("type") or "").strip()
        date_str = (data.get("date") or "").strip()
        commentaire = (data.get("commentaire") or "").strip()

        if not dossier_ref or not type_label or not date_str:
            return _json_error("Champs obligatoires manquants")

        dossier_obj = TechnicalProject.objects.filter(reference=dossier_ref).first()
        if not dossier_obj:
            return _json_error(f'Dossier introuvable : "{dossier_ref}"', status=404)

        type_obj = TypeActivite.objects.filter(type__iexact=type_label).first()
        if not type_obj:
            types_disponibles = ", ".join(
                TypeActivite.objects.order_by("type").values_list("type", flat=True)
            )
            return _json_error(
                f'Type invalide. Types autorisés : {types_disponibles}'
            )

        date_activite = _parse_iso_datetime(date_str)

        max_id_result = Activite.objects.aggregate(max_id=Max("id"))["max_id"]
        next_id = 1 if max_id_result is None else int(max_id_result) + 1

        nouvelle_activite = Activite.objects.create(
            id=next_id,
            dossier=dossier_obj,
            type=type_obj,
            date=date_activite,
            date_type="date",
            commentaire=commentaire or None,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Activité créée avec succès",
                "activity_id": nouvelle_activite.id,
                "activity": {
                    "id": nouvelle_activite.id,
                    "dossier": dossier_obj.reference,
                    "dossier_nom": getattr(dossier_obj, "name", dossier_obj.reference),
                    "type": type_obj.type,
                    "date": nouvelle_activite.date.isoformat(),
                    "commentaire": nouvelle_activite.commentaire or "",
                },
            }
        )

    except ValueError as e:
        return _json_error(str(e))
    except Exception as e:
        traceback.print_exc()
        return _json_error(f"Erreur : {str(e)}", status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def delete_activity_view(request):
    """
    Supprime une ou plusieurs activités correspondant aux critères donnés.
    """
    try:
        data = _parse_request_json(request)

        dossier_ref = (data.get("dossier") or "").strip()
        type_label = (data.get("type") or "").strip()
        date_str = (data.get("date") or "").strip()

        if not dossier_ref or not type_label or not date_str:
            return _json_error("Champs obligatoires manquants")

        dossier_obj = TechnicalProject.objects.filter(reference=dossier_ref).first()
        if not dossier_obj:
            return _json_error(f'Dossier introuvable : "{dossier_ref}"', status=404)

        type_obj = TypeActivite.objects.filter(type__iexact=type_label).first()
        if not type_obj:
            return _json_error(f'Type introuvable : "{type_label}"', status=404)

        date_activite = _parse_iso_datetime(date_str)
        date_debut = date_activite.replace(second=0, microsecond=0)
        date_fin = date_debut + timedelta(minutes=1)

        queryset = Activite.objects.filter(
            dossier=dossier_obj,
            type=type_obj,
            date__gte=date_debut,
            date__lt=date_fin,
        )

        count_before = queryset.count()
        if count_before == 0:
            return _json_error(
                "Aucune activité ne correspond à ces critères",
                status=404,
            )

        deleted_count, _ = queryset.delete()

        return JsonResponse(
            {
                "success": True,
                "message": f"{deleted_count} activité(s) supprimée(s) avec succès",
                "deleted_count": deleted_count,
            }
        )

    except ValueError as e:
        return _json_error(f"Format de date invalide : {str(e)}")
    except Exception as e:
        traceback.print_exc()
        return _json_error(f"Erreur : {str(e)}", status=500)