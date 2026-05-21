import json
import traceback
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from technique.models import TechnicalProject
from user_access.user_test_functions import has_administratif_access

from .email_manager import (
    create_outlook_event,
    delete_outlook_event,
    fetch_new_emails,
    get_email_summary,
    get_sent_emails,
    send_email_reply,
    update_outlook_event,
)
from .models import (
    Activite,
    NotificationInterne,
    TypeActivite,
)

Utilisateur = get_user_model()

STATUS_COLORS = {
    "todo": "#64748b",
    "in_progress": "#2563eb",
    "done": "#16a34a",
    "cancelled": "#dc2626",
}

PRIORITY_COLORS = {
    "low": "#64748b",
    "normal": "#0ea5e9",
    "high": "#f97316",
    "urgent": "#dc2626",
}


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

    parsed = datetime.fromisoformat(value)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value or "").lower() in {"1", "true", "on", "yes", "oui"}


def _next_activity_id():
    numeric_ids = []
    for value in Activite.objects.values_list("id", flat=True):
        if str(value).isdigit():
            numeric_ids.append(int(value))
    return str(max(numeric_ids, default=0) + 1)


def _user_label(user):
    if not user:
        return ""
    full_name = user.get_full_name()
    return full_name or user.get_username()


def _serialize_activity(activity, include_datetime=False):
    date_value = activity.date
    is_overdue = bool(
        date_value
        and date_value < timezone.now()
        and activity.statut not in {"done", "cancelled"}
    )
    dossier_reference = getattr(activity.dossier, "reference", "") or ""
    dossier_nom = getattr(activity.dossier, "name", "") or dossier_reference
    payload = {
        "id": activity.id,
        "titre": activity.titre or "",
        "dossier": dossier_reference,
        "dossier_nom": dossier_nom,
        "type": getattr(activity.type, "type", "") or "",
        "date": date_value.strftime("%Y-%m-%d") if date_value else "",
        "commentaire": activity.commentaire or "",
        "statut": activity.statut,
        "statut_label": activity.get_statut_display(),
        "priorite": activity.priorite,
        "priorite_label": activity.get_priorite_display(),
        "responsable_id": activity.responsable_id or "",
        "responsable_label": _user_label(activity.responsable),
        "client": activity.client or "",
        "contact_externe": activity.contact_externe or "",
        "is_overdue": is_overdue,
        "status_color": STATUS_COLORS.get(activity.statut, STATUS_COLORS["todo"]),
        "priority_color": PRIORITY_COLORS.get(activity.priorite, PRIORITY_COLORS["normal"]),
        "outlook_synced": bool(activity.outlook_event_id),
    }
    if include_datetime:
        payload.update(
            {
                "time": date_value.strftime("%H:%M") if date_value else "09:00",
                "datetime": date_value.isoformat() if date_value else None,
            }
        )
    return payload


def _apply_calendar_filters(queryset, params):
    type_label = (params.get("type") or "").strip()
    dossier_ref = (params.get("dossier") or "").strip()
    responsable = (params.get("responsable") or "").strip()
    statut = (params.get("statut") or "").strip()
    priorite = (params.get("priorite") or "").strip()
    client = (params.get("client") or "").strip()
    contact = (params.get("contact") or "").strip()
    date_from = (params.get("date_from") or "").strip()
    date_to = (params.get("date_to") or "").strip()

    if type_label:
        queryset = queryset.filter(type__type__iexact=type_label)
    if dossier_ref:
        queryset = queryset.filter(dossier__reference=dossier_ref)
    if responsable:
        queryset = queryset.filter(responsable_id=responsable)
    if statut:
        queryset = queryset.filter(statut=statut)
    if priorite:
        queryset = queryset.filter(priorite=priorite)
    if client:
        queryset = queryset.filter(client__icontains=client)
    if contact:
        queryset = queryset.filter(contact_externe__icontains=contact)
    if date_from:
        queryset = queryset.filter(date__date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())
    if date_to:
        queryset = queryset.filter(date__date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
    return queryset


def _activity_form_data(data):
    dossier_ref = (data.get("dossier") or "").strip()
    type_label = (data.get("type") or "").strip()
    date_str = (data.get("date") or "").strip()

    if not dossier_ref or not type_label or not date_str:
        raise ValueError("Champs obligatoires manquants")

    dossier_obj = TechnicalProject.objects.filter(reference=dossier_ref).first()
    if not dossier_obj:
        raise LookupError(f'Dossier introuvable : "{dossier_ref}"')

    type_obj = TypeActivite.objects.filter(type__iexact=type_label).first()
    if not type_obj:
        types_disponibles = ", ".join(
            TypeActivite.objects.order_by("type").values_list("type", flat=True)
        )
        raise ValueError(f'Type invalide. Types autorisés : {types_disponibles}')

    responsable_id = (data.get("responsable") or "").strip()
    responsable = None
    if responsable_id:
        responsable = Utilisateur.objects.filter(pk=responsable_id, is_active=True).first()
        if not responsable:
            raise ValueError("Responsable introuvable")

    statut = (data.get("statut") or "todo").strip()
    priorite = (data.get("priorite") or "normal").strip()
    if statut not in dict(Activite.STATUTS):
        raise ValueError("Statut invalide")
    if priorite not in dict(Activite.PRIORITES):
        raise ValueError("Priorité invalide")

    return {
        "titre": (data.get("titre") or "").strip(),
        "dossier": dossier_obj,
        "type": type_obj,
        "date": _parse_iso_datetime(date_str),
        "date_type": "date",
        "commentaire": (data.get("commentaire") or "").strip() or None,
        "statut": statut,
        "priorite": priorite,
        "responsable": responsable,
        "client": (data.get("client") or "").strip(),
        "contact_externe": (data.get("contact_externe") or "").strip(),
    }


def _sync_outlook_after_save(request, activity, sync_requested):
    if sync_requested:
        result = (
            update_outlook_event(request.user, activity)
            if activity.outlook_event_id
            else create_outlook_event(request.user, activity)
        )
        if result.get("success"):
            event_id = result.get("event_id")
            if event_id and activity.outlook_event_id != event_id:
                activity.outlook_event_id = event_id
                activity.save(update_fields=["outlook_event_id"])
            return ""
        return result.get("message") or "Synchronisation Outlook impossible."

    if activity.outlook_event_id:
        event_id = activity.outlook_event_id
        result = delete_outlook_event(request.user, event_id)
        activity.outlook_event_id = ""
        activity.save(update_fields=["outlook_event_id"])
        if not result.get("success"):
            return result.get("message") or "L'événement Outlook n'a pas pu être supprimé."
    return ""


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
    users = Utilisateur.objects.filter(is_active=True).order_by(
        "last_name",
        "first_name",
        "username",
    )
    notifications = list(
        NotificationInterne.objects.filter(user=user, is_read=False)
        .select_related("activite")
        .order_by("-created_at")[:8]
    )

    return render(
        request,
        "management.html",
        {
            "pole_name": "Administratif",
            "emails": emails_data,
            "dossiers": dossiers,
            "types": types,
            "users": users,
            "notifications": notifications,
            "notification_count": len(notifications),
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

        start_date = timezone.make_aware(datetime(year, month, 1))
        end_date = (
            timezone.make_aware(datetime(year + 1, 1, 1))
            if month == 12
            else timezone.make_aware(datetime(year, month + 1, 1))
        )

        activites = (
            Activite.objects.filter(
                date__gte=start_date,
                date__lt=end_date,
            )
            .select_related("dossier", "type", "responsable")
            .order_by("date", "id")
        )
        activites = _apply_calendar_filters(activites, request.GET)

        activites_list = [_serialize_activity(act, include_datetime=True) for act in activites]

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

        start_dt = timezone.make_aware(datetime(monday.year, monday.month, monday.day, 0, 0, 0))
        end_dt = timezone.make_aware(datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59))

        activites = (
            Activite.objects.filter(
                date__gte=start_dt,
                date__lte=end_dt,
            )
            .select_related("dossier", "type", "responsable")
            .order_by("date", "id")
        )
        activites = _apply_calendar_filters(activites, request.GET)

        activites_list = [_serialize_activity(act, include_datetime=True) for act in activites]

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
        activity_data = _activity_form_data(data)
        if not activity_data["titre"]:
            activity_data["titre"] = f"{activity_data['type'].type} - {activity_data['dossier'].reference}"

        nouvelle_activite = Activite.objects.create(
            id=_next_activity_id(),
            created_by=request.user,
            updated_by=request.user,
            **activity_data,
        )
        warning = _sync_outlook_after_save(
            request,
            nouvelle_activite,
            _truthy(data.get("sync_outlook")),
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Activité créée avec succès",
                "warning": warning,
                "activity_id": nouvelle_activite.id,
                "activity": _serialize_activity(nouvelle_activite, include_datetime=True),
            }
        )

    except LookupError as e:
        return _json_error(str(e), status=404)
    except ValueError as e:
        return _json_error(str(e))
    except Exception as e:
        traceback.print_exc()
        return _json_error(f"Erreur : {str(e)}", status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def update_activity_view(request, activity_id):
    """
    Met à jour une activité existante depuis le calendrier.
    """
    try:
        data = _parse_request_json(request)
        activity = (
            Activite.objects.select_related("dossier", "type", "responsable")
            .filter(pk=activity_id)
            .first()
        )
        if not activity:
            return _json_error("Activité introuvable", status=404)

        activity_data = _activity_form_data(data)
        if not activity_data["titre"]:
            activity_data["titre"] = f"{activity_data['type'].type} - {activity_data['dossier'].reference}"

        for field, value in activity_data.items():
            setattr(activity, field, value)
        activity.updated_by = request.user
        activity.save()

        warning = _sync_outlook_after_save(
            request,
            activity,
            _truthy(data.get("sync_outlook")),
        )

        activity.refresh_from_db()
        return JsonResponse(
            {
                "success": True,
                "message": "Activité mise à jour avec succès",
                "warning": warning,
                "activity": _serialize_activity(activity, include_datetime=True),
            }
        )

    except LookupError as e:
        return _json_error(str(e), status=404)
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
        activity_id = (data.get("activity_id") or data.get("id") or "").strip()

        if activity_id:
            activity = Activite.objects.filter(pk=activity_id).first()
            if not activity:
                return _json_error("Activité introuvable", status=404)

            warning = ""
            if activity.outlook_event_id:
                result = delete_outlook_event(request.user, activity.outlook_event_id)
                if not result.get("success"):
                    warning = result.get("message") or "L'événement Outlook n'a pas pu être supprimé."
            activity.delete()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Activité supprimée avec succès",
                    "warning": warning,
                    "deleted_count": 1,
                }
            )

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

        warning = ""
        for activity in queryset:
            if activity.outlook_event_id:
                result = delete_outlook_event(request.user, activity.outlook_event_id)
                if not result.get("success") and not warning:
                    warning = result.get("message") or "Un événement Outlook n'a pas pu être supprimé."

        deleted_count, _ = queryset.delete()

        return JsonResponse(
            {
                "success": True,
                "message": f"{deleted_count} activité(s) supprimée(s) avec succès",
                "warning": warning,
                "deleted_count": deleted_count,
            }
        )

    except ValueError as e:
        return _json_error(f"Format de date invalide : {str(e)}")
    except Exception as e:
        traceback.print_exc()
        return _json_error(f"Erreur : {str(e)}", status=500)


@require_http_methods(["POST"])
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def mark_notification_read_view(request, notification_id):
    updated = NotificationInterne.objects.filter(
        pk=notification_id,
        user=request.user,
    ).update(is_read=True)
    if not updated:
        return _json_error("Notification introuvable", status=404)
    return JsonResponse({"success": True})
