# signatures/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.utils import timezone

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
from .services.pdf_signing import get_pdf_last_page_info, get_signature_block_metrics
from .services.email import envoyer_demande_signature
from user_access.user_test_functions import (
    has_administratif_access,
    has_all_poles_access,
    has_ceo_access,
)


SIGNATURE_SIGNER_LABEL = "CEO ou pôle administratif"
DEFAULT_SIGNATURE_SCALE = 100.0
DEFAULT_SIGNATURE_MODE = "stamp_signature"


def _has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def _can_manage_signature_assets(user):
    return has_ceo_access(user) or has_administratif_access(user)


def _can_delete_signature_documents(user):
    return has_ceo_access(user) or has_administratif_access(user)


def _can_supervise_signature_documents(user):
    return user.is_superuser


def _get_admin_signature_users():
    User = get_user_model()
    return (
        User.objects.filter(groups__name="POLE_ADMINISTRATIF", is_active=True)
        .exclude(is_superuser=True)
        .exclude(email="")
        .distinct()
        .order_by("first_name", "last_name", "username")
    )


def _get_ceo_signature_users():
    User = get_user_model()
    return (
        User.objects.filter(is_superuser=True, is_active=True)
        .exclude(email="")
        .distinct()
    )


def _get_signature_email_recipients(designated_signer=None):
    emails = []

    if designated_signer and designated_signer.email:
        emails.append(designated_signer.email)

    emails.extend(user.email for user in _get_ceo_signature_users() if user.email)

    destinataires = []
    deja_vus = set()
    for email in emails:
        cle = email.lower()
        if cle not in deja_vus:
            deja_vus.add(cle)
            destinataires.append(email)
    return destinataires


def _active_tampons():
    return Tampon.objects.filter(is_active=True).order_by("societe", "nom")


def _get_selected_signature_options(data):
    signature_mode = (data.get("signature_mode") or DEFAULT_SIGNATURE_MODE).strip()
    if signature_mode not in dict(Document.SIGNATURE_MODES):
        raise ValueError("Mode de signature invalide.")

    tampon = None
    if signature_mode == "stamp_signature":
        tampon_id = (data.get("tampon_id") or "").strip()
        tampon = _active_tampons().filter(pk=tampon_id).first()
        if not tampon:
            raise ValueError("Veuillez sélectionner un tampon actif.")
    return signature_mode, tampon


def _signature_preview_context(doc, size_scale_pct=DEFAULT_SIGNATURE_SCALE, signature_mode=DEFAULT_SIGNATURE_MODE):
    page_info = get_pdf_last_page_info(doc)
    block_metrics = get_signature_block_metrics(size_scale_pct, signature_mode=signature_mode)
    signature_only_metrics = get_signature_block_metrics(size_scale_pct, signature_mode="signature")
    stamp_signature_metrics = get_signature_block_metrics(size_scale_pct, signature_mode="stamp_signature")
    page_width = page_info["page_width"] or 1
    page_height = page_info["page_height"] or 1

    block_width_pct = (block_metrics["block_width"] / page_width) * 100
    block_height_pct = (block_metrics["block_height"] / page_height) * 100
    signature_only_width_pct = (signature_only_metrics["block_width"] / page_width) * 100
    signature_only_height_pct = (signature_only_metrics["block_height"] / page_height) * 100
    stamp_signature_width_pct = (stamp_signature_metrics["block_width"] / page_width) * 100
    stamp_signature_height_pct = (stamp_signature_metrics["block_height"] / page_height) * 100

    return {
        "pdf_page_count": page_info["page_count"],
        "pdf_page_width": page_width,
        "pdf_page_height": page_height,
        "pdf_page_width_css": f"{page_width:.4f}",
        "pdf_page_height_css": f"{page_height:.4f}",
        "pdf_page_ratio": page_width / page_height,
        "signature_scale_pct": size_scale_pct,
        "signature_scale_pct_css": f"{size_scale_pct:.4f}",
        "signature_block_width_pct": block_width_pct,
        "signature_block_height_pct": block_height_pct,
        "signature_block_width_pct_css": f"{block_width_pct:.4f}",
        "signature_block_height_pct_css": f"{block_height_pct:.4f}",
        "signature_only_block_width_pct_css": f"{signature_only_width_pct:.4f}",
        "signature_only_block_height_pct_css": f"{signature_only_height_pct:.4f}",
        "stamp_signature_block_width_pct_css": f"{stamp_signature_width_pct:.4f}",
        "stamp_signature_block_height_pct_css": f"{stamp_signature_height_pct:.4f}",
        "signature_mode": signature_mode,
        "signature_mode_label": dict(Document.SIGNATURE_MODES).get(signature_mode, signature_mode),
    }


def _can_user_sign_document(user, document):
    if not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or _has_group(user, "POLE_ADMINISTRATIF")
    )


def _get_pending_signature_requests_for_user(user):
    pending_requests = SignatureRequest.objects.filter(statut="pending")
    if _can_supervise_signature_documents(user):
        return pending_requests
    return pending_requests.filter(approver=user)


def _signature_document_visibility_filter(user):
    return (
        Q(uploaded_by=user)
        | Q(demandes_signature__requested_by=user)
        | Q(demandes_signature__approver=user)
    )


def _visible_signature_documents(user):
    queryset = Document.objects.all()
    if _can_supervise_signature_documents(user):
        return queryset

    return queryset.filter(
        Q(fichier_signe__isnull=True)
        | Q(fichier_signe="")
        | _signature_document_visibility_filter(user)
    ).distinct()


def _can_user_view_signature_document(user, document):
    if _can_supervise_signature_documents(user):
        return True
    if not document.fichier_signe:
        return True
    if document.uploaded_by_id == user.id:
        return True
    return document.demandes_signature.filter(
        Q(requested_by=user) | Q(approver=user)
    ).exists()


def _can_user_approve_signature_request(user, demande):
    if not user.is_authenticated:
        return False

    return (
        user == demande.approver
        or user.is_superuser
    )


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def document_list(request):
    """
    Liste des documents avec un statut "intelligent" :
    - Signé si fichier_signe présent
    - En attente de signature si une demande pending existe
    - Sinon, dernier statut de l'historique
    """

    if (
        has_ceo_access(request.user)
        or _get_pending_signature_requests_for_user(request.user).exists()
    ):
        return redirect("signatures:ceo_dashboard")

    documents = (
        _visible_signature_documents(request.user)
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
        {
            "documents": documents,
            "can_delete_documents": _can_delete_signature_documents(request.user),
        },
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
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()
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
    if not _can_user_view_signature_document(request.user, doc):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à consulter ce document signé.")
    is_designated_signer = _can_user_sign_document(request.user, doc)
    historiques = doc.historique.order_by("-date_action")

    pending_request = doc.demandes_signature.filter(statut="pending").first()

    is_signed = bool(doc.fichier_signe)

    requester_name = None
    request_date = None
    if pending_request:
        requester_name = pending_request.requested_by.get_full_name() or pending_request.requested_by.username
        request_date = pending_request.created_at

    return render(
        request,
        "signatures/document_detail.html",
        {
            "doc": doc,
            "historiques": historiques,
            "pending_request": pending_request,
            "requester_name": requester_name,
            "request_date": request_date,
            "is_designated_signer": is_designated_signer,
            "signer_label": SIGNATURE_SIGNER_LABEL,
            "is_signed": is_signed,
        },
    )




@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def document_update(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not _can_user_view_signature_document(request.user, doc):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à modifier ce document.")
    messages.error(request, "La modification des documents a signer n'est plus autorisee.")
    return redirect("signatures:document_detail", pk=doc.pk)

    # Règle métier : si déjà signé, on bloque l'édition du fichier
    is_signed = bool(doc.fichier_signe)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, instance=doc)

        if form.is_valid():
            # Si signé, empêcher toute tentative de remplacement de fichier
            if is_signed and "fichier" in form.changed_data:
                messages.error(
                    request,
                    "Document déjà signé : le fichier ne peut plus être modifié.",
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

    return render(request, "signatures/document_update.html", {"doc": doc, "form": form, "is_signed": is_signed})

@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def envoyer_signature(request, pk):
    """
    Ancienne action "mettre en attente de signature".
    On n'affiche plus le bouton dans l'UI, mais on laisse la vue au cas où.
    """
    doc = get_object_or_404(Document, pk=pk)
    if not _can_user_view_signature_document(request.user, doc):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à agir sur ce document.")
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

    return render(request, "signatures/ma_signature.html", {"form": form})


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
@user_passes_test(_can_manage_signature_assets, login_url="/signatures", redirect_field_name=None)
def tampon_edit(request):
    """
    Permet de créer/modifier les tampons numériques par société.
    """
    tampon_id = request.POST.get("tampon_id") or request.GET.get("tampon_id")
    tampon = Tampon.objects.filter(pk=tampon_id).first() if tampon_id else None

    if request.method == "POST":
        form = TamponForm(request.POST, request.FILES, instance=tampon)
        if form.is_valid():
            form.save()
            messages.success(request, "Tampon enregistré.")
            return redirect("signatures:tampon_edit")
    else:
        form = TamponForm(instance=tampon)

    return render(
        request,
        "signatures/tampon_edit.html",
        {
            "form": form,
            "tampon": tampon,
            "tampons": Tampon.objects.all().order_by("societe", "nom"),
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
    if not _can_user_view_signature_document(request.user, doc):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à consulter ce document.")

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
        → placement + création d'une demande de signature pour les signataires autorisés.

    Une fois qu'une demande est en attente pour ce document,
    les employés ne peuvent plus re-placer la signature.
    Si le document est déjà signé, plus personne ne peut accéder à cette page.
    """
    doc = get_object_or_404(Document, pk=pk)
    is_designated_signer = _can_user_sign_document(request.user, doc)
    signer_label = SIGNATURE_SIGNER_LABEL
    admin_signers = _get_admin_signature_users()
    tampons = _active_tampons()

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
            size_scale = float(request.POST.get("size_scale_pct") or DEFAULT_SIGNATURE_SCALE)
        except (TypeError, ValueError):
            messages.error(request, "Position invalide.")
            return redirect("signatures:placer_signature", pk=doc.pk)

        try:
            signature_mode, tampon = _get_selected_signature_options(request.POST)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("signatures:placer_signature", pk=doc.pk)

        size_scale = min(max(size_scale, 50.0), 150.0)

        # BRANCHE SIGNATAIRE : il signe directement
        if is_designated_signer:
            try:
                signer_document_avec_position(
                    document=doc,
                    user=request.user,
                    pos_x_pct=pos_x,
                    pos_y_pct=pos_y,
                    size_scale_pct=size_scale,
                    signature_mode=signature_mode,
                    tampon=tampon,
                )
            except Exception as e:
                HistoriqueSignature.objects.create(
                    document=doc,
                    statut="erreur",
                    commentaire=f"Erreur lors de la signature directe par le signataire autorisé : {e}",
                )
                messages.error(
                    request,
                    f"Erreur lors de la génération du document signé : {e}",
                )
                return redirect("signatures:document_detail", pk=doc.pk)

            HistoriqueSignature.objects.create(
                document=doc,
                statut="signe",
                commentaire=f"Document signé directement par un signataire autorisé ({doc.get_signature_mode_display()}).",
            )

            # On peut marquer d'éventuelles demandes en attente comme expirées
            SignatureRequest.objects.filter(
                document=doc,
                statut="pending",
            ).update(statut="expired", decided_at=timezone.now())

            messages.success(request, "Document signé avec succès.")
            return redirect("signatures:document_detail", pk=doc.pk)

        # BRANCHE EMPLOYÉ : création d'une demande pour le membre administratif choisi
        selected_admin_id = request.POST.get("admin_signer_id")
        designated_signer = admin_signers.filter(pk=selected_admin_id).first()
        email_recipients = _get_signature_email_recipients(designated_signer)
        if not designated_signer or not email_recipients:
            messages.error(
                request,
                "Veuillez sélectionner un membre du pôle administratif à notifier.",
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
            size_scale_pct=size_scale,
            signature_mode=signature_mode,
            tampon=tampon,
        )

        # Mettre à jour l'historique
        HistoriqueSignature.objects.create(
            document=doc,
            statut="en_attente",
            commentaire=(
                "Demande de signature envoyée au membre administratif choisi et aux CEO : "
                f"{', '.join(email_recipients)}. Mode : {demande.get_signature_mode_display()}."
            ),
        )

        # Construire l'URL d'approbation
        from django.urls import reverse

        approval_url = request.build_absolute_uri(
            reverse("signatures:signature_approval", args=[demande.token])
        )

        # Utilisation du service email
        try:
            envoyer_demande_signature(email_recipients, approval_url, doc)
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
    context = {
        "doc": doc,
        "is_designated_signer": is_designated_signer,
        "signer_label": signer_label,
        "admin_signers": admin_signers,
        "tampons": tampons,
        "signature_mode_choices": Document.SIGNATURE_MODES,
        "default_signature_mode": DEFAULT_SIGNATURE_MODE,
    }
    context.update(_signature_preview_context(doc))
    return render(request, "signatures/placer_signature.html", context)


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def signature_approval(request, token):
    """
    Page d'approbation signataire : le lien contient un token.
    Un signataire autorisé voit le doc + position prévue, et peut approuver ou refuser.
    """
    demande = get_object_or_404(SignatureRequest, token=token)

    # Double sécurité : il faut être le membre choisi ou un CEO.
    if not _can_user_approve_signature_request(request.user, demande):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à valider cette demande.")

    doc = demande.document

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
                    signature_mode=demande.signature_mode,
                    tampon=demande.tampon,
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
                commentaire=f"Document signé et approuvé par un signataire autorisé ({doc.get_signature_mode_display()}).",
            )
            messages.success(request, "Document signé et approuvé.")
            return redirect("signatures:document_detail", pk=doc.pk)

        elif action == "refuse":
            demande.marquer_refusee(commentaire)
            HistoriqueSignature.objects.create(
                document=doc,
                statut="refuse",
                commentaire="Demande refusée par un signataire autorisé.",
            )
            messages.info(request, "Demande de signature refusée.")
            return redirect("signatures:document_detail", pk=doc.pk)

    # GET : on montre l'aperçu, la position, et les boutons Approuver / Refuser
    context = {
        "doc": doc,
        "demande": demande,
        "signature_request_pos_x_css": f"{demande.pos_x_pct:.4f}",
        "signature_request_pos_y_css": f"{demande.pos_y_pct:.4f}",
        "requester_name": demande.requested_by.get_full_name() or demande.requested_by.username,
        "formatted_date": demande.created_at.strftime("%d/%m/%Y à %H:%M"),
        "signature_mode_label": demande.get_signature_mode_display(),
        "selected_tampon": demande.tampon,
    }
    context.update(_signature_preview_context(doc, demande.size_scale_pct, demande.signature_mode))
    return render(request, "signatures/signature_approval.html", context)


@login_required
@user_passes_test(has_all_poles_access, login_url="/", redirect_field_name=None)
def ceo_dashboard(request):
    """
    Tableau de bord du signataire :
    - Demandes en attente (actionnable)
    - Historique global des 50 derniers documents (tout confondu : signés direct ou via demande)
    """
    pending_requests = (
        _get_pending_signature_requests_for_user(request.user)
        .select_related("document", "requested_by")
        .order_by("-created_at")
    )

    # Historique global : on prend les Documents directement
    documents_history = (
        _visible_signature_documents(request.user)
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


# ================== Suppression en masse ==================

@login_required
@user_passes_test(_can_delete_signature_documents, login_url="/", redirect_field_name=None)
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
