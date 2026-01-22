# signatures/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
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
from .services.email import envoyer_demande_signature
from user_access.user_test_functions import (has_ceo_access, has_finance_access)


@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def document_list(request):
    """
    Liste des documents avec un statut "intelligent" :
    - Signé si fichier_signe présent
    - En attente de signature si une demande pending existe
    - Sinon, dernier statut de l'historique
    """

    if has_ceo_access(request.user):
        return redirect("signatures:ceo_dashboard")

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
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
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
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def document_detail(request, pk):
    """
    Affiche une vue qui présente les informations d'un document

    Args:
        request (HttpRequest) : Requête HTTP
        pk (int): Identifiant du document
    """
    doc = get_object_or_404(Document, pk=pk)
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
            "is_ceo": has_ceo_access(request.user),
            "is_signed": is_signed,
        },
    )


@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
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
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def ma_signature(request):
    """
    Permet à l'utilisateur courant (ex : CEO) de déposer/modifier son image de signature.
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
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
@user_passes_test(has_ceo_access, login_url="/signatures", redirect_field_name=None)
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

    return render(request, "signatures/tampon_edit.html", {"form": form})


@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
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
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def placer_signature(request, pk):
    """
    Page de placement du bloc tampon+signature.

    - Si l'utilisateur est CEO :
        → placement + signature immédiate du document.
    - Si l'utilisateur est un employé :
        → placement + création d'une SignatureRequest pour le CEO.

    Une fois qu'une demande est en attente pour ce document,
    les employés ne peuvent plus re-placer la signature.
    Si le document est déjà signé, plus personne ne peut accéder à cette page.
    """
    doc = get_object_or_404(Document, pk=pk)

    # 1) Si déjà signé → on bloque tout
    if doc.fichier_signe:
        messages.info(request, "Ce document est déjà signé.")
        return redirect("signatures:document_detail", pk=doc.pk)

    # 2) Si employé (non-CEO) et qu'il existe déjà une demande pending → on bloque
    existing_pending = doc.demandes_signature.filter(statut="pending").first()
    if not has_ceo_access(request.user) and existing_pending:
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
        except (TypeError, ValueError):
            messages.error(request, "Position invalide.")
            return redirect("signatures:placer_signature", pk=doc.pk)

        # BRANCHE CEO : il signe directement
        if has_ceo_access(request.user):
            try:
                signer_document_avec_position(
                    document=doc,
                    user=request.user,
                    pos_x_pct=pos_x,
                    pos_y_pct=pos_y,
                )
            except Exception as e:
                HistoriqueSignature.objects.create(
                    document=doc,
                    statut="erreur",
                    commentaire=f"Erreur lors de la signature directe par le CEO : {e}",
                )
                messages.error(
                    request,
                    f"Erreur lors de la génération du document signé : {e}",
                )
                return redirect("signatures:document_detail", pk=doc.pk)

            HistoriqueSignature.objects.create(
                document=doc,
                statut="signe",
                commentaire="Document signé directement par le CEO.",
            )

            # On peut marquer d'éventuelles demandes en attente comme expirées
            SignatureRequest.objects.filter(
                document=doc,
                statut="pending",
            ).update(statut="expired", decided_at=timezone.now())

            messages.success(request, "Document signé avec succès.")
            return redirect("signatures:document_detail", pk=doc.pk)

        # BRANCHE EMPLOYÉ : création d'une demande pour le CEO
        User = get_user_model()
        # ceo = User.objects.filter(groups__name="CEO").first()
        ceo = User.objects.filter(groups__name="CEO").first()
        if not ceo or not ceo.email:
            messages.error(
                request,
                "Aucun CEO configuré pour recevoir la demande.",
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
            approver=ceo,
            pos_x_pct=pos_x,
            pos_y_pct=pos_y,
        )

        # Mettre à jour l'historique
        HistoriqueSignature.objects.create(
            document=doc,
            statut="en_attente",
            commentaire=f"Demande de signature envoyée au CEO ({ceo.email}).",
        )

        # Construire l'URL d'approbation
        from django.urls import reverse

        approval_url = request.build_absolute_uri(
            reverse("signatures:signature_approval", args=[demande.token])
        )

        # Utilisation du service email
        try:
            envoyer_demande_signature(ceo.email, approval_url, doc)
        except Exception as e:
            messages.warning(
                request,
                f"Demande créée, mais l'email n'a pas pu être envoyé : {e}",
            )

        messages.success(
            request,
            "Demande de signature envoyée au CEO. En attente de validation.",
        )
        return redirect("signatures:document_detail", pk=doc.pk)

    # GET : on affiche la page avec l'aperçu et le bloc draggable
    return render(
        request,
        "signatures/placer_signature.html",
        {
            "doc": doc,
            "is_ceo": has_ceo_access,
        },
    )


@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
@user_passes_test(has_ceo_access, login_url="/signatures", redirect_field_name=None)
def signature_approval(request, token):
    """
    Page d'approbation CEO : le lien contient un token.
    Le CEO voit le doc + position prévue, et peut approuver ou refuser.
    """
    demande = get_object_or_404(SignatureRequest, token=token)

    # Double sécurité : il faut être le bon approver (CEO)
    if request.user != demande.approver:
        return HttpResponseForbidden("Vous n'êtes pas autorisé à valider cette demande.")

    doc = demande.document

    if demande.statut != "pending":
        messages.info(
            request,
            f"Cette demande a déjà été traitée (statut : {demande.get_statut_display()}).",
        )
        return redirect("signatures:document_detail", pk=doc.pk)

    # ✅ CORRECTION ICI : "POST" et pas "POST__"
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
                )
            except Exception as e:
                demande.marquer_refusee(commentaire=f"Erreur technique : {e}")
                HistoriqueSignature.objects.create(
                    document=doc,
                    statut="erreur",
                    commentaire=f"Erreur lors de la signature par le CEO : {e}",
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
                commentaire="Document signé et approuvé par le CEO.",
            )
            messages.success(request, "Document signé et approuvé.")
            return redirect("signatures:document_detail", pk=doc.pk)

        elif action == "refuse":
            demande.marquer_refusee(commentaire)
            HistoriqueSignature.objects.create(
                document=doc,
                statut="refuse",
                commentaire="Demande refusée par le CEO.",
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
    return render(request, "signatures/signature_approval.html", context)


@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
@user_passes_test(has_ceo_access, login_url="/signatures", redirect_field_name=None)
def ceo_dashboard(request):
    """
    Tableau de bord du CEO :
    - Demandes en attente (actionnable)
    - Historique global des 50 derniers documents (tout confondu : signés direct ou via demande)
    """
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


# ================== Suppression en masse ==================

@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
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
            f"✅ {deleted_count} document{'s' if deleted_count > 1 else ''} supprimé{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la suppression : {str(e)}")
    
    return redirect("signatures:document_list")
