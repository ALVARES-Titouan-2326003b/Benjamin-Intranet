# signatures/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.conf import settings
from pypdf import PdfReader

from .models import (
    Document,
    SignatureUser,
    Tampon,
    SignatureRequest,
    HistoriqueSignature,
)
from .forms import (
    DocumentUploadForm,
    SignatureUserForm,
    TamponForm,
    PlacementForm,
)
from .services.workflow import (
    init_workflow,
    lancer_signature,
    signer_document_avec_position,
)
from .services.email import envoyer_demande_signature
from user_access.user_test_functions import (
    has_administratif_access,
    has_all_poles_access,
    has_ceo_access,
)


def _has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def _can_manage_signature_assets(user):
    return has_ceo_access(user) or has_administratif_access(user)


def _get_designated_signer(document):
    """
    Retourne l'utilisateur désigné pour signer ce document selon sa catégorie.
    """
    User = get_user_model()

    if document.signataire_requis == "CEO":
        return User.objects.filter(groups__name="CEO").first()

    admin_username = getattr(settings, "SIGNATURE_ADMIN_USERNAME", None)
    if not admin_username:
        admin_username = getattr(settings, "SIGNATURE_RH_USERNAME", None)
    if admin_username:
        admin_by_username = User.objects.filter(username=admin_username).first()
        if admin_by_username:
            return admin_by_username

    # On cible en priorité un membre du pôle administratif qui n'est pas CEO.
    admin_user = (
        User.objects.filter(groups__name="POLE_ADMINISTRATIF")
        .exclude(groups__name="CEO")
        .first()
    )
    if admin_user:
        return admin_user

    return User.objects.filter(groups__name="POLE_ADMINISTRATIF").first()


def _can_user_sign_document(user, document):
    if not user.is_authenticated:
        return False

    if document.signataire_requis == "CEO":
        return _has_group(user, "CEO")

    return user.is_superuser or user.is_staff or _has_group(user, "POLE_ADMINISTRATIF")


def _get_pdf_preview_metadata(document):
    """
    Retourne les dimensions de la dernière page du PDF, qui est la page
    réellement signée par le service PDF.
    """
    default_metadata = {
        "preview_page_number": 1,
        "preview_page_width": 595.0,
        "preview_page_height": 842.0,
    }

    try:
        reader = PdfReader(document.fichier.path)
        page_count = len(reader.pages)
        if page_count == 0:
            return default_metadata

        last_page = reader.pages[-1]
        return {
            "preview_page_number": page_count,
            "preview_page_width": float(last_page.mediabox.width),
            "preview_page_height": float(last_page.mediabox.height),
        }
    except Exception:
        return default_metadata


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def document_list(request):
    """
    Liste des documents avec un statut "intelligent" :
    - Signé si fichier_signe présent
    - En attente de signature si une demande pending existe
    - Sinon, dernier statut de l'historique
    """

    if _can_manage_signature_assets(request.user) or SignatureRequest.objects.filter(
        approver=request.user,
        statut="pending",
    ).exists():
        return redirect("signatures:signer_dashboard")

    documents = (
        Document.objects
        .order_by("-date_upload")
        .prefetch_related("historique", "demandes_signature")
    )

    STATUS_CONFIG = {
        "upload": ("Ajouté", "sig-badge-upload"),
        "en_attente": ("En attente de signature", "sig-badge-attente"),
        "signe": ("Signé", "sig-badge-signe"),
        "refuse": ("Refusé", "sig-badge-refuse"),
        "erreur": ("Erreur", "sig-badge-erreur"),
    }

    for doc in documents:
        last = doc.historique.order_by("-date_action").first()

        if doc.fichier_signe:
            key = "signe"
        elif doc.demandes_signature.filter(statut="pending").exists():
            key = "en_attente"
        elif last:
            key = last.statut
        else:
            key = "upload"

        label, css = STATUS_CONFIG.get(key, (key, ""))
        doc.status_key = key
        doc.status_label = label
        doc.status_css = css

    return render(
        request,
        "signatures/document_list.html",
        {"documents": documents},
    )


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def upload_document(request):
    """
    Affiche une vue permettant d'enregistrer un document
    """
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save()
            init_workflow(doc)
            messages.success(request, "Document ajouté.")
            return redirect("signatures:document_detail", pk=doc.pk)
    else:
        form = DocumentUploadForm()

    return render(request, "signatures/upload_document.html", {"form": form})


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def document_detail(request, pk):
    """
    Affiche une vue qui présente les informations d'un document

    Args:
        request (HttpRequest) : Requête HTTP
        pk (int): Identifiant du document
    """
    doc = get_object_or_404(Document, pk=pk)
    designated_signer = _get_designated_signer(doc)
    is_designated_signer = _can_user_sign_document(request.user, doc)
    historiques = doc.historique.order_by("-date_action")

    pending_request = doc.demandes_signature.filter(statut="pending").first()
    latest_request = doc.demandes_signature.select_related("requested_by").order_by("-created_at").first()

    is_signed = bool(doc.fichier_signe)

    requester_name = None
    request_date = None
    if latest_request:
        requester_name = latest_request.requested_by.get_full_name() or latest_request.requested_by.username
        request_date = latest_request.created_at

    target_pole = "CEO" if doc.signataire_requis == "CEO" else "Administratif"

    return render(
        request,
        "signatures/document_detail.html",
        {
            "doc": doc,
            "historiques": historiques,
            "pending_request": pending_request,
            "requester_name": requester_name,
            "request_date": request_date,
            "target_pole": target_pole,
            "is_ceo_user": has_ceo_access(request.user),
            "has_signer_dashboard_access": _can_manage_signature_assets(request.user),
            "is_designated_signer": is_designated_signer,
            "designated_signer_name": (
                designated_signer.get_full_name() or designated_signer.username
            ) if designated_signer else None,
            "is_signed": is_signed,
        },
    )




@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def document_update(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    messages.error(request, "La modification des documents a signer n'est plus autorisee.")
    return redirect("signatures:document_detail", pk=doc.pk)

    # Règle métier : si déjà signé, on bloque l'édition du fichier
    is_signed = bool(doc.fichier_signe)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, instance=doc)

        if form.is_valid():
            # Si signé, empêcher toute tentative de remplacement de fichier
            if is_signed and ("fichier" in form.changed_data or "signataire_requis" in form.changed_data):
                messages.error(
                    request,
                    "Document déjà signé : le fichier et le signataire ne peuvent plus être modifiés.",
                )
                return redirect("signatures:document_detail", pk=doc.pk)

            form.save()
            messages.success(request, "Document modifié.")
            return redirect("signatures:document_detail", pk=doc.pk)
    else:
        form = DocumentUploadForm(instance=doc)

        # Option UX : si signé, rendre le champ fichier non modifiable dans le form
        if is_signed:
            form.fields["fichier"].disabled = True
            form.fields["signataire_requis"].disabled = True

    return render(request, "signatures/document_update.html", {"doc": doc, "form": form, "is_signed": is_signed})

@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def envoyer_signature(request, pk):
    """
    Ancienne action "mettre en attente de signature".
    On n'affiche plus le bouton dans l'UI, mais on laisse la vue au cas où.
    """
    doc = get_object_or_404(Document, pk=pk)
    lancer_signature(doc)
    messages.info(request, "Document mis en attente de signature.")
    return redirect("signatures:document_detail", pk=doc.pk)


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def ma_signature(request):
    """
    Permet à l'utilisateur courant de déposer/modifier son image de signature.
    """
    try:
        instance = request.user.signature_profile  # lié à SignatureUser.user
    except SignatureUser.DoesNotExist:
        instance = None

    if request.method == "POST":
        form = SignatureUserForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            signature_obj = form.save(commit=False)
            signature_obj.user = request.user
            signature_obj.save()
            messages.success(request, "Votre signature a été enregistrée.")
            return redirect("signatures:ma_signature")
    else:
        form = SignatureUserForm(instance=instance)

    return render(
        request,
        "signatures/ma_signature.html",
        {
            "form": form,
            "signature_user": instance,
        },
    )


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
@user_passes_test(_can_manage_signature_assets, login_url="/signatures", redirect_field_name=None)
def tampon_edit(request):
    """
    Permet de créer/modifier le tampon numérique global.
    On suppose qu'il n'y en a qu'un.
    """
    tampon, _ = Tampon.objects.get_or_create(pk=1)  # un seul tampon global

    if request.method == "POST":
        form = TamponForm(request.POST, request.FILES, instance=tampon)
        if form.is_valid():
            form.save()
            messages.success(request, "Tampon mis à jour.")
            return redirect("signatures:tampon_edit")
    else:
        form = TamponForm(instance=tampon)

    return render(
        request,
        "signatures/tampon_edit.html",
        {
            "form": form,
            "tampon": tampon,
        },
    )


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def config_placement(request, pk):
    """
    (Optionnel) Permet de définir manuellement des positions en base.
    Tu peux le garder pour des tests avancés.
    """
    doc = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        form = PlacementForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, "Placement mis à jour.")
            return redirect("signatures:document_detail", pk=doc.pk)
    else:
        form = PlacementForm(instance=doc)

    return render(
        request,
        "signatures/config_placement.html",
        {"doc": doc, "form": form},
    )


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def placer_signature(request, pk):
    """
    Page de placement du bloc tampon+signature.

    - Si l'utilisateur est autorisé à signer ce document :
        → placement + signature immédiate du document.
    - Sinon :
        → placement + création d'une demande de signature pour le signataire cible.

    Une fois qu'une demande est en attente pour ce document,
    les employés ne peuvent plus re-placer la signature.
    Si le document est déjà signé, plus personne ne peut accéder à cette page.
    """
    doc = get_object_or_404(Document, pk=pk)
    designated_signer = _get_designated_signer(doc)
    is_designated_signer = _can_user_sign_document(request.user, doc)
    signer_label = doc.get_signataire_requis_display()
    preview_metadata = _get_pdf_preview_metadata(doc)

    # 1) Si déjà signé → on bloque tout
    if doc.fichier_signe:
        messages.info(request, "Ce document est déjà signé.")
        return redirect("signatures:document_detail", pk=doc.pk)

    # 2) Si le demandeur n'est pas signataire et qu'il existe déjà une demande pending → on bloque
    existing_pending = doc.demandes_signature.filter(statut="pending").first()
    if not is_designated_signer and existing_pending:
        messages.info(
            request,
            "Une demande de signature est déjà en attente pour ce document. "
            "Vous ne pouvez plus modifier le placement.",
        )
        return redirect("signatures:document_detail", pk=doc.pk)

    if request.method == "POST":
        try:
            pos_x = float(request.POST.get("pos_x_pct"))
            pos_y = float(request.POST.get("pos_y_pct"))
            size_scale_pct = float(request.POST.get("size_scale_pct", 100))
        except (TypeError, ValueError):
            messages.error(request, "Position ou taille invalide.")
            return redirect("signatures:placer_signature", pk=doc.pk)

        # BRANCHE SIGNATAIRE : il signe directement
        if is_designated_signer:
            try:
                signer_document_avec_position(
                    document=doc,
                    user=request.user,
                    pos_x_pct=pos_x,
                    pos_y_pct=pos_y,
                    size_scale_pct=size_scale_pct,
                )
            except Exception as e:
                HistoriqueSignature.objects.create(
                    document=doc,
                    statut="erreur",
                    commentaire=f"Erreur lors de la signature directe par le signataire : {e}",
                )
                messages.error(
                    request,
                    f"Erreur lors de la génération du document signé : {e}",
                )
                return redirect("signatures:document_detail", pk=doc.pk)

            HistoriqueSignature.objects.create(
                document=doc,
                statut="signe",
                commentaire="Document signé directement par le signataire désigné.",
            )

            # On peut marquer d'éventuelles demandes en attente comme expirées
            SignatureRequest.objects.filter(
                document=doc,
                statut="pending",
            ).update(statut="expired", decided_at=timezone.now())

            messages.success(request, "Document signé avec succès.")
            return redirect("signatures:document_detail", pk=doc.pk)

        # BRANCHE EMPLOYÉ : création d'une demande pour le signataire désigné
        if not designated_signer or not designated_signer.email:
            messages.error(
                request,
                f"Aucun signataire configuré pour '{signer_label}'.",
            )
            return redirect("signatures:document_detail", pk=doc.pk)

        # Double check : si quelqu'un a créé une demande entre-temps
        existing_pending = doc.demandes_signature.filter(statut="pending").first()
        if existing_pending:
            messages.info(
                request,
                "Une demande de signature a déjà été créée pendant votre action.",
            )
            return redirect("signatures:document_detail", pk=doc.pk)

        # Créer la demande de signature
        demande = SignatureRequest.objects.create(
            document=doc,
            requested_by=request.user,
            approver=designated_signer,
            pos_x_pct=pos_x,
            pos_y_pct=pos_y,
            size_scale_pct=size_scale_pct,
        )

        # Mettre à jour l'historique
        HistoriqueSignature.objects.create(
            document=doc,
            statut="en_attente",
            commentaire=(
                "Demande de signature envoyée à "
                f"{designated_signer.get_full_name() or designated_signer.username}"
                f" ({designated_signer.email})."
            ),
        )

        # Construire l'URL d'approbation
        from django.urls import reverse

        approval_url = request.build_absolute_uri(
            reverse("signatures:signature_approval", args=[demande.token])
        )

        # Utilisation du service email
        try:
            envoyer_demande_signature(designated_signer.email, approval_url, doc)
        except Exception as e:
            messages.warning(
                request,
                f"Demande créée, mais l'email n'a pas pu être envoyé : {e}",
            )

        messages.success(
            request,
            "Demande de signature envoyée. En attente de validation.",
        )
        return redirect("signatures:document_detail", pk=doc.pk)

    # GET : on affiche la page avec l'aperçu et le bloc draggable
    return render(
        request,
        "signatures/placer_signature.html",
        {
            "doc": doc,
            "is_designated_signer": is_designated_signer,
            "default_size_scale_pct": 100,
            **preview_metadata,
            "designated_signer_name": (
                designated_signer.get_full_name() or designated_signer.username
            ) if designated_signer else signer_label,
        },
    )


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def signature_approval(request, token):
    """
    Page d'approbation signataire : le lien contient un token.
    Le signataire désigné voit le doc + position prévue, et peut approuver ou refuser.
    """
    demande = get_object_or_404(SignatureRequest, token=token)

    # Double sécurité : il faut être le bon approver
    if request.user != demande.approver and not _can_user_sign_document(request.user, demande.document):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à valider cette demande.")

    doc = demande.document
    preview_metadata = _get_pdf_preview_metadata(doc)

    if demande.statut != "pending":
        messages.info(
            request,
            f"Cette demande a déjà été traitée (statut : {demande.get_statut_display()}).",
        )
        return redirect("signatures:document_detail", pk=doc.pk)

    if request.method == "POST":
        action = request.POST.get("action")
        commentaire = request.POST.get("commentaire", "")

        if action == "approve":
            # On génère réellement le PDF signé ici :
            try:
                signer_document_avec_position(
                    document=doc,
                    user=request.user,
                    pos_x_pct=demande.pos_x_pct,
                    pos_y_pct=demande.pos_y_pct,
                    size_scale_pct=demande.size_scale_pct,
                )
            except Exception as e:
                demande.marquer_refusee(commentaire=f"Erreur technique : {e}")
                HistoriqueSignature.objects.create(
                    document=doc,
                    statut="erreur",
                    commentaire=f"Erreur lors de la signature par le signataire : {e}",
                )
                messages.error(
                    request,
                    f"Erreur lors de la génération du document signé : {e}",
                )
                return redirect("signatures:document_detail", pk=doc.pk)

            demande.marquer_approuvee(commentaire)
            HistoriqueSignature.objects.create(
                document=doc,
                statut="signe",
                commentaire="Document signé et approuvé par le signataire désigné.",
            )
            messages.success(request, "Document signé et approuvé.")
            return redirect("signatures:document_detail", pk=doc.pk)

        elif action == "refuse":
            demande.marquer_refusee(commentaire)
            HistoriqueSignature.objects.create(
                document=doc,
                statut="refuse",
                commentaire="Demande refusée par le signataire désigné.",
            )
            messages.info(request, "Demande de signature refusée.")
            return redirect("signatures:document_detail", pk=doc.pk)

    # GET : on montre l'aperçu, la position, et les boutons Approuver / Refuser
    context = {
        "doc": doc,
        "demande": demande,
        "requester_name": demande.requested_by.get_full_name() or demande.requested_by.username,
        "formatted_date": demande.created_at.strftime("%d/%m/%Y à %H:%M"),
    }
    context.update(preview_metadata)
    return render(request, "signatures/signature_approval.html", context)


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def signer_dashboard(request):
    """
    Tableau de bord du signataire :
    - Demandes en attente (actionnable)
    - Historique global des 50 derniers documents (tout confondu : signés direct ou via demande)
    """
    if not _can_manage_signature_assets(request.user) and not SignatureRequest.objects.filter(
        approver=request.user,
        statut="pending",
    ).exists():
        messages.error(request, "Vous n'avez pas accès au tableau de bord des signatures.")
        return redirect("signatures:document_list")

    pending_requests = (
        SignatureRequest.objects.filter(
            approver=request.user,
            statut="pending",
        )
        .select_related("document", "requested_by")
        .order_by("-created_at")
    )

    # Historique global : on prend les Documents directement
    documents_history = (
        Document.objects.all()
        .order_by("-date_upload")[:50]
        .prefetch_related("historique", "demandes_signature__requested_by")
    )

    # Réutilisation de la logique de statut de document_list
    STATUS_CONFIG = {
        "upload": ("Ajouté", "sig-badge-upload"),
        "en_attente": ("En attente de signature", "sig-badge-attente"),
        "signe": ("Signé", "status-payee"),  # mapping vers classe CSS existante ou nouvelle
        "refuse": ("Refusé", "status-refusee"),
        "erreur": ("Erreur", "sig-badge-erreur"),
    }

    for doc in documents_history:
        last = doc.historique.order_by("-date_action").first()

        if doc.fichier_signe:
            key = "signe"
        elif doc.demandes_signature.filter(statut="pending").exists():
            key = "en_attente"
        elif last:
            key = last.statut
        else:
            key = "upload"

        label, css = STATUS_CONFIG.get(key, (key, ""))
        doc.status_key = key
        doc.status_label = label
        # Utilisation des classes CSS du dashboard si possible, sinon fallback
        if key == "signe":
            doc.status_css = "status-payee"
        elif key == "refuse":
            doc.status_css = "status-refusee"
        elif key == "en_attente":
            doc.status_css = "status-encours"
        else:
            doc.status_css = "status-encours" # Default/Upload

        # Tenter de trouver le demandeur (le plus récent)
        last_request = doc.demandes_signature.order_by("-created_at").first()
        doc.last_request = last_request
        doc.last_action_date = last.date_action if last else doc.date_upload
        
        if last_request:
            doc.requester_name = last_request.requested_by.get_full_name() or last_request.requested_by.username
        else:
            doc.requester_name = None

    return render(
        request,
        "signatures/ceo_dashboard.html",
        {
            "pending_requests": pending_requests,
            "documents_history": documents_history,
        },
    )


ceo_dashboard = signer_dashboard


# ================== Suppression en masse ==================

@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def bulk_delete_documents(request):
    """
    Vue pour supprimer plusieurs documents en une seule action
    """
    if request.method != "POST":
        return redirect("signatures:document_list")
    
    # Récupérer les IDs des documents sélectionnés
    document_ids = request.POST.getlist('document_ids')
    
    if not document_ids:
        messages.warning(request, "Aucun document sélectionné.")
        return redirect("signatures:document_list")
    
    try:
        # Supprimer les documents
        deleted_count = Document.objects.filter(id__in=document_ids).delete()[0]
        
        messages.success(
            request,
            f"{deleted_count} document{'s' if deleted_count > 1 else ''} supprimé{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression : {str(e)}")
    
    return redirect("signatures:document_list")
