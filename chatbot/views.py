import json
import re

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from invoices.models import Facture
from invoices.views import visible_invoices_for
from technique.models import DocumentTechnique
from user_access.user_test_functions import can_view_technical_dossiers

from .legifrance import format_legifrance_context, legifrance_search_generic
from .models import ChatbotQuery
from .services.case_context import append_sources, build_case_context, resolve_case


INVOICE_STATUS_MAP = {
    "recu": "received",
    "reçue": "received",
    "reçues": "received",
    "received": "received",
    "en attente": "pending",
    "attente": "pending",
    "pending": "pending",
}
SUMMARY_KEYWORDS = {"stats", "résumé", "resume", "total", "synthèse", "synthese"}
LIST_KEYWORDS = {"liste", "toutes", "all"}

_ROUTER_SYSTEM = (
    "Tu routes les questions d'un assistant intranet immobilier. "
    "Réponds avec un seul mot parmi :\n"
    "- case : synthèse d'une affaire ou d'un dossier, budget, dépenses, dates clés, actions ou risques ;\n"
    "- invoice : factures, fournisseurs, montants et statuts sans dossier précis ;\n"
    "- document : clauses, contrats et documents techniques internes ;\n"
    "- legal : droit immobilier et réglementation générale."
)


@login_required
def chatbot_history(request):
    query_type = (request.GET.get("type") or "").strip()
    search = (request.GET.get("q") or "").strip()
    queries = ChatbotQuery.objects.filter(user=request.user).order_by("-created_at")
    if query_type:
        queries = queries.filter(query_type=query_type)
    if search:
        queries = queries.filter(message__icontains=search)
    return render(
        request,
        "chatbot/history.html",
        {"queries": queries, "selected_type": query_type, "search": search},
    )


def _route_message(message):
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return _route_fallback(message)
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": 0,
                "max_tokens": 10,
                "messages": [
                    {"role": "system", "content": _ROUTER_SYSTEM},
                    {"role": "user", "content": message},
                ],
            },
            timeout=10,
        )
        if response.status_code == 200:
            route = response.json()["choices"][0]["message"]["content"].strip().lower()
            if route in {"case", "invoice", "document", "legal"}:
                return route
    except Exception:
        pass
    return _route_fallback(message)


def _route_fallback(message):
    lowered = message.lower()
    case_words = {
        "affaire",
        "dossier",
        "budget",
        "dépense",
        "dépenses",
        "date clé",
        "dates clés",
        "action en retard",
        "actions en retard",
    }
    invoice_words = {"facture", "factures", "fournisseur", "paiement"}
    document_words = {
        "contrat",
        "document",
        "clause",
        "permis",
        "procès-verbal",
        "conditions suspensives",
    }
    has_case_reference = bool(re.search(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b", message.upper()))
    if any(word in lowered for word in case_words):
        return "case"
    if any(word in lowered for word in invoice_words):
        return "invoice"
    if has_case_reference:
        return "case"
    if any(word in lowered for word in document_words):
        return "document"
    return "legal"


def _groq_answer(system_prompt, context, message, max_tokens=900):
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.1,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": context},
                    {"role": "user", "content": message},
                ],
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
    return None


def _handle_case_query(message, user):
    resolution = resolve_case(message, user)
    if resolution.is_ambiguous:
        choices = "\n".join(
            f"- **{project.reference}** — {project.name}" for project in resolution.alternatives
        )
        return "Plusieurs dossiers correspondent. Précisez la référence souhaitée :\n" + choices
    if resolution.project is None:
        return (
            "Je n’ai trouvé aucun dossier accessible correspondant à cette question. "
            "Indiquez sa référence exacte ou une partie suffisamment précise de son nom."
        )

    context = build_case_context(resolution.project, user)
    system_prompt = (
        "Tu es l'assistant interne de Benjamin Immobilier. Réponds uniquement à partir de "
        "l'instantané du dossier fourni. Croise les factures, le budget, les dates, les actions "
        "et les documents quand cela répond à la question. N'invente aucune donnée. Signale "
        "explicitement les informations absentes. Commence par une réponse directe puis détaille "
        "les échéances ou risques utiles. Ne reproduis pas une source qui n'est pas fournie."
    )
    answer = _groq_answer(system_prompt, context.prompt, message)
    if not answer:
        return context.fallback_answer
    return append_sources(answer, context.sources)


def _build_rag_context(question, user, max_docs=4, max_chars_per_doc=1200):
    """Recherche documentaire limitée aux utilisateurs du pôle technique."""
    if not getattr(user, "is_authenticated", False) or not can_view_technical_dossiers(user):
        return ""
    stopwords = {
        "pour", "avec", "dans", "quel", "quoi", "les", "des", "une", "cette",
        "sont", "quels", "quelle", "quelles", "comment", "quand", "peut", "doit",
    }
    words = [word for word in re.findall(r"\b\w{4,}\b", question.lower()) if word not in stopwords]
    if not words:
        return ""
    query = Q()
    for word in words[:6]:
        query |= (
            Q(resume__icontains=word)
            | Q(texte_brut__icontains=word)
            | Q(titre__icontains=word)
            | Q(project__reference__icontains=word)
            | Q(project__name__icontains=word)
        )
    documents = DocumentTechnique.objects.select_related("project").filter(query).order_by("-created_at")[:max_docs]
    blocks = []
    for document in documents:
        content = document.resume or document.texte_brut or ""
        if not content.strip():
            continue
        extras = [
            text
            for text in (
                f"Prix/montants : {document.prix}" if document.prix else "",
                f"Dates clés : {document.dates}" if document.dates else "",
                f"Conditions suspensives : {document.conditions_suspensives}" if document.conditions_suspensives else "",
                f"Pénalités : {document.penalites}" if document.penalites else "",
            )
            if text
        ]
        excerpt = f"{content}\n{' '.join(extras)}".strip()[:max_chars_per_doc]
        blocks.append(f"--- Document : {document.titre} | Dossier : {document.project or '—'} ---\n{excerpt}")
    if not blocks:
        return ""
    return "Extraits de documents internes autorisés :\n\n" + "\n\n".join(blocks)


def _handle_document_query(message, user):
    context = _build_rag_context(message, user)
    if not context:
        return "Aucun document interne accessible ne correspond à cette question."
    prompt = (
        "Réponds uniquement à partir des extraits internes. Cite le titre du document utilisé. "
        "Si l'information est absente, indique-le clairement."
    )
    return _groq_answer(prompt, context, message, max_tokens=800) or context


def _user_queryset(user):
    queryset = Facture.objects.select_related("client", "fournisseur", "dossier")
    return visible_invoices_for(user, queryset)


def _invoice_by_id(invoice_id, user):
    try:
        invoice = _user_queryset(user).get(id=invoice_id)
    except Facture.DoesNotExist:
        return f"Aucune facture accessible trouvée avec l’ID {invoice_id}"
    return (
        f"Facture #{invoice.id}\n"
        f"- État : {invoice.get_statut_display()}\n"
        f"- Fournisseur : {invoice.fournisseur}\n"
        f"- Montant : {invoice.montant} €\n"
        f"- Dossier : {invoice.dossier or '—'}\n"
        f"- Échéance : {invoice.echeance.strftime('%d/%m/%Y') if invoice.echeance else '—'}"
    )


def _invoices_by_status(status, user):
    invoices = _user_queryset(user).filter(statut=status).order_by("-echeance")[:5]
    label = dict(Facture.STATUS).get(status, status)
    if not invoices:
        return f"Aucune facture avec le statut {label}."
    rows = [f"Factures « {label} » :"]
    rows.extend(f"- #{item.id} — {item.fournisseur} — {item.montant} €" for item in invoices)
    return "\n".join(rows)


def _invoices_by_supplier(supplier, user):
    invoices = _user_queryset(user).filter(fournisseur__nom__icontains=supplier).order_by("-echeance")[:5]
    if not invoices:
        return f"Aucune facture accessible pour « {supplier} »"
    rows = [f"Factures — {supplier} :"]
    rows.extend(f"- #{item.id} — {item.get_statut_display()} — {item.montant} €" for item in invoices)
    return "\n".join(rows)


def _invoices_all(user, limit=20):
    invoices = _user_queryset(user).order_by("-date_soumission")[:limit]
    if not invoices:
        return "Aucune facture accessible."
    return "Toutes les factures accessibles :\n" + "\n".join(
        f"- #{item.id} — {item.get_statut_display()} — {item.fournisseur} — {item.montant} €"
        for item in invoices
    )


def _invoices_summary(user):
    invoices = list(_user_queryset(user))
    if not invoices:
        return "Aucune facture accessible."
    total = sum(item.montant or 0 for item in invoices)
    return f"Résumé des factures\n- Total : {len(invoices)}\n- Montant cumulé : {total:,.2f} €".replace(",", " ")


def _invoice_ai_context(user, limit=100):
    """Instantané financier borné, limité aux factures visibles par l'utilisateur."""
    invoices = list(
        _user_queryset(user)
        .select_related("societe", "fournisseur", "dossier", "created_by")
        .order_by("-date_soumission", "-id")[:limit]
    )
    lines = ["FACTURES AUTORISÉES (les plus récentes en premier)"]
    sources = []
    for invoice in invoices:
        lines.append(
            f"- {invoice.id} | n° {invoice.numero_facture or '—'} | société {invoice.societe or '—'} | "
            f"dossier {invoice.dossier or 'Divers'} | fournisseur {invoice.fournisseur} | "
            f"montant {invoice.montant or 0} € | statut {invoice.get_statut_display()} | "
            f"pôle {invoice.get_service_display() or '—'} | facture {invoice.date_facture or '—'} | "
            f"échéance {invoice.echeance or '—'} | ajout {invoice.date_soumission:%d/%m/%Y}"
            + (f" | commentaire {invoice.commentaire_compta}" if invoice.commentaire_compta else "")
        )
        if len(sources) < 12:
            sources.append((f"Facture {invoice.id}", reverse("invoices:detail", args=[invoice.pk])))
    return "\n".join(lines), tuple(sources)


def _extract_existing_invoice_id(text, user):
    for token in re.findall(r"\b[A-Z]{3,}-[A-Z0-9-]{4,}\b", text.upper()):
        if _user_queryset(user).filter(id=token).exists():
            return token
    return None


def _handle_invoice_query(message, user):
    invoice_id = _extract_existing_invoice_id(message, user)
    if invoice_id:
        return _invoice_by_id(invoice_id, user)
    if re.search(r"\b[A-Z]{3,}-[A-Z0-9-]{4,}\b", message.upper()):
        return "Aucune facture accessible ne correspond à cette référence."
    lowered = message.lower()
    if any(word in lowered for word in SUMMARY_KEYWORDS):
        return _invoices_summary(user)
    if any(word in lowered for word in LIST_KEYWORDS):
        return _invoices_all(user)
    for key in sorted(INVOICE_STATUS_MAP, key=len, reverse=True):
        if key in lowered:
            return _invoices_by_status(INVOICE_STATUS_MAP[key], user)
    match = re.search(r"fournisseur\s+(.+)$", message, flags=re.I)
    if match:
        return _invoices_by_supplier(match.group(1).strip(), user)

    context, sources = _invoice_ai_context(user)
    answer = _groq_answer(
        "Tu es l'assistant financier interne. Réponds uniquement à partir des factures autorisées "
        "fournies. Tu peux filtrer, comparer, totaliser et signaler des échéances. N'invente rien et "
        "indique clairement lorsqu'une donnée est absente.",
        context,
        message,
        max_tokens=900,
    )
    if answer:
        return append_sources(answer, sources)
    return _invoices_by_supplier(message.strip(), user)


def _handle_legal_query(message):
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return "Clé API Groq manquante"
    try:
        result = legifrance_search_generic(message, page_size=5)
        context = format_legifrance_context(result, max_items=3)
    except Exception as exc:
        context = f"Légifrance indisponible : {exc}"
    prompt = (
        "Tu es un assistant juridique en droit immobilier français. Distingue les informations "
        "certaines des éléments à vérifier et recommande un professionnel pour toute décision importante."
    )
    return _groq_answer(prompt, context, message, max_tokens=700) or "Le service juridique est temporairement indisponible."


@login_required
def chatbot_interface(request):
    return render(request, "chatbot/interface.html")


@login_required
def chatbot_query(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "response": "Méthode non autorisée"}, status=405)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "response": "Requête JSON invalide."}, status=400)
    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"success": False, "response": "Message vide."}, status=400)

    route = _route_message(message)
    handlers = {
        "case": lambda: _handle_case_query(message, request.user),
        "invoice": lambda: _handle_invoice_query(message, request.user),
        "document": lambda: _handle_document_query(message, request.user),
        "legal": lambda: _handle_legal_query(message),
    }
    try:
        answer = handlers[route]()
        ChatbotQuery.objects.create(
            user=request.user,
            message=message,
            response=answer,
            query_type=route,
        )
        return JsonResponse({"success": True, "response": answer, "query_type": route})
    except Exception:
        answer = "Une erreur interne empêche momentanément de répondre à cette question."
        ChatbotQuery.objects.create(
            user=request.user,
            message=message,
            response=answer,
            query_type="unknown",
        )
        return JsonResponse({"success": False, "response": answer}, status=500)
