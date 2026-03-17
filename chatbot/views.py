from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import re
import requests

from invoices.models import Facture
from .legifrance import legifrance_search_generic, format_legifrance_context
from .models import ChatbotQuery


@login_required
def chatbot_interface(request):
    """Affiche l'interface du chatbot."""
    return render(request, 'chatbot/interface.html')


@csrf_exempt
@login_required
def chatbot_query(request):
    """
    Route unique :
      - si message concerne les factures -> interroge la BD
      - sinon -> question juridique via Groq (+ Légifrance)

    Si la route facture ne trouve rien, on fait un fallback vers le juridique.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'response': 'Méthode non autorisée'}, status=405)

    message = ""
    try:
        data = json.loads(request.body or '{}')
        message = (data.get('message') or '').strip()

        if not message:
            return JsonResponse({'success': False, 'response': 'Message vide.'}, status=400)

        route = "unknown"

        if _is_invoice_query(message):
            route = "invoice"
            resp = _handle_invoice_query(message, request.user)

            if resp.startswith("Aucune facture") or resp.startswith("🕳️ Aucune facture"):
                route = "legal_fallback"
                resp = _handle_legal_query(message)
        else:
            route = "legal"
            resp = _handle_legal_query(message)

        ChatbotQuery.objects.create(
            user=request.user,
            message=message,
            response=resp,
            query_type=route,
        )

        return JsonResponse({
            'success': True,
            'response': resp,
            'query_type': route,
        })

    except Exception as e:
        error_message = f'Erreur: {e}'

        if request.user.is_authenticated and message:
            ChatbotQuery.objects.create(
                user=request.user,
                message=message,
                response=error_message,
                query_type="unknown",
            )

        return JsonResponse({'success': False, 'response': error_message}, status=500)

@login_required
def chatbot_history(request):
    """
    Affiche l'historique des requêtes du chatbot
    pour l'utilisateur connecté uniquement.
    """
    query_type = (request.GET.get("type") or "").strip()
    search = (request.GET.get("q") or "").strip()

    qs = ChatbotQuery.objects.filter(user=request.user).order_by("-created_at")

    if query_type:
        qs = qs.filter(query_type=query_type)

    if search:
        qs = qs.filter(message__icontains=search)

    return render(
        request,
        "chatbot/history.html",
        {
            "queries": qs,
            "selected_type": query_type,
            "search": search,
        },
    )


# Factures

INVOICE_STATUS_MAP = {
    'payee': 'Payee', 'payée': 'Payee', 'payé': 'Payee', 'paid': 'Payee',
    'recu': 'Recue', 'reçue': 'Recue',
    'en cours': 'En cours', 'progress': 'En cours',
    'refusee': 'Refusee', 'refusée': 'Refusee', 'rejected': 'Refusee',
    'archivee': 'Archivee', 'archivée': 'Archivee', 'archive': 'Archivee',
    'en retard': 'En retard', 'retard': 'En retard',
}

# Résumé ou liste
SUMMARY_KEYWORDS = {'stats', 'résumé', 'resume', 'total', 'synthèse', 'synthese'}
LIST_KEYWORDS = {'liste', 'toutes', 'all'}


from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import re
import requests

from invoices.models import Facture
from .legifrance import legifrance_search_generic, format_legifrance_context
from .models import ChatbotQuery


# ══════════════════════════════════════════════════════════════════
#  ROUTING IA
#  Remplace l'ancienne détection par mots-clés (_is_invoice_query)
#  par un appel Groq léger qui classe l'intention en 3 catégories.
# ══════════════════════════════════════════════════════════════════

_ROUTER_SYSTEM = (
    "Tu es un routeur de requêtes pour un assistant intranet d'une agence immobilière.\n"
    "Classe la question de l'utilisateur dans UNE SEULE des catégories suivantes :\n"
    "- 'invoice'  : question sur des factures, fournisseurs, paiements, statuts de factures, montants\n"
    "- 'document' : question sur des contrats, documents techniques, projets immobiliers internes, "
    "clauses, conditions suspensives, permis de construire, procès-verbaux, résumés de documents\n"
    "- 'legal'    : question juridique générale sur le droit immobilier, les lois, la réglementation, "
    "les baux, le DPE, la fiscalité, la copropriété, etc.\n\n"
    "Réponds UNIQUEMENT avec le mot exact : invoice, document ou legal. Rien d'autre."
)


def _route_message(message: str) -> str:
    """
    Appelle Groq pour classifier l'intention du message.
    Retourne 'invoice', 'document' ou 'legal'.
    Fallback sur 'legal' en cas d'erreur ou de réponse inattendue.
    """
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        # Pas de clé : fallback sur la détection par mots-clés
        return _route_fallback(message)

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.0,
                "max_tokens": 10,
                "messages": [
                    {"role": "system", "content": _ROUTER_SYSTEM},
                    {"role": "user",   "content": message},
                ],
            },
            timeout=10,
        )
        if r.status_code == 200:
            intent = r.json()["choices"][0]["message"]["content"].strip().lower()
            if intent in ("invoice", "document", "legal"):
                return intent
        # Réponse inattendue : fallback
        return _route_fallback(message)

    except Exception:
        return _route_fallback(message)


def _route_fallback(message: str) -> str:
    """
    Détection par mots-clés utilisée si Groq est indisponible.
    Conserve le comportement historique + ajoute la catégorie 'document'.
    """
    m = message.lower()
    has_invoice_id = bool(re.search(r'\b[A-Z]{3,}-[A-Z0-9]{4,}\b', message))
    invoice_kw = ['facture', 'factures', 'fournisseur', 'statut', 'liste', 'total', 'combien', 'stats']
    doc_kw = ['contrat', 'document', 'clause', 'permis', 'procès-verbal', 'résumé', 'projet technique',
              'conditions suspensives', 'pénalités', 'délais', 'vefa', 'réservation']

    if has_invoice_id or any(k in m for k in invoice_kw):
        return "invoice"
    if any(k in m for k in doc_kw):
        return "document"
    return "legal"


# ══════════════════════════════════════════════════════════════════
#  RAG — DOCUMENTS TECHNIQUES
#  Recherche les passages les plus pertinents dans DocumentTechnique
#  et les injecte dans le prompt Groq.
# ══════════════════════════════════════════════════════════════════

def _build_rag_context(question: str, max_docs: int = 4, max_chars_per_doc: int = 1200) -> str:
    """
    Recherche dans DocumentTechnique les documents dont le résumé ou le texte
    contient des mots de la question, et construit un bloc de contexte textuel.

    Stratégie simple (pas de vecteurs) :
      1. On extrait les mots significatifs de la question (> 3 caractères).
      2. On filtre les documents qui matchent au moins un mot dans titre/projet/resume.
      3. On tronque le texte_brut pour rester dans les limites du contexte.
    """
    try:
        from technique.models import DocumentTechnique, TechnicalProject
    except ImportError:
        return ""

    # Mots-clés de la question (> 3 lettres, hors stop-words courants)
    stopwords = {"pour", "avec", "dans", "quel", "quoi", "est", "les", "des", "une", "que",
                 "pas", "plus", "tout", "mais", "cette", "sont", "quel", "quels", "quelle",
                 "quelles", "comment", "quand", "peut", "peut-on", "doit", "doit-on"}
    words = [w for w in re.findall(r'\b\w{4,}\b', question.lower()) if w not in stopwords]

    if not words:
        return ""

    from django.db.models import Q
    q_filter = Q()
    for w in words[:6]:          # On limite à 6 mots pour ne pas surcharger la requête
        q_filter |= Q(resume__icontains=w) | Q(titre__icontains=w) | Q(projet__icontains=w)

    docs = DocumentTechnique.objects.filter(q_filter).order_by("-created_at")[:max_docs]

    if not docs:
        return ""

    blocks = []
    for doc in docs:
        # On préfère le résumé structuré (plus dense) au texte brut complet
        content = doc.resume or doc.texte_brut or ""
        if not content.strip():
            continue

        # Ajouter les champs structurés si disponibles
        extras = []
        if doc.prix and doc.prix not in ("—", "Non identifié"):
            extras.append(f"Prix/montants : {doc.prix}")
        if doc.dates and doc.dates not in ("—", "Non identifié"):
            extras.append(f"Dates clés : {doc.dates}")
        if doc.conditions_suspensives and doc.conditions_suspensives not in ("—", "Non identifié"):
            extras.append(f"Conditions suspensives : {doc.conditions_suspensives}")
        if doc.penalites and doc.penalites not in ("—", "Non identifié"):
            extras.append(f"Pénalités : {doc.penalites}")

        extra_text = "\n".join(extras)
        full = f"{content}\n{extra_text}".strip()[:max_chars_per_doc]

        blocks.append(
            f"--- Document : {doc.titre} | Projet : {doc.projet or '—'} | "
            f"Type : {doc.get_type_document_display()} ---\n{full}"
        )

    if not blocks:
        return ""

    return (
        "Extraits de documents internes Benjamin Immobilier pertinents pour cette question :\n\n"
        + "\n\n".join(blocks)
    )


def _handle_document_query(message: str) -> str:
    """
    Répond à une question sur les documents techniques internes.
    Injecte le contexte RAG dans le prompt Groq.
    """
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return "Clé API Groq manquante."

    rag_context = _build_rag_context(message)

    system_prompt = (
        "Tu es un assistant spécialisé dans les documents techniques et juridiques "
        "de l'entreprise Benjamin Immobilier (promoteur immobilier).\n"
        "Tu réponds aux questions en te basant PRIORITAIREMENT sur les documents internes fournis.\n"
        "Si les documents ne contiennent pas l'information, dis-le clairement et donne une réponse "
        "générale basée sur tes connaissances du droit immobilier français.\n"
        "Sois précis, concis et cite le nom du document source quand tu utilises son contenu."
    )

    messages_payload = [{"role": "system", "content": system_prompt}]

    if rag_context:
        messages_payload.append({
            "role": "system",
            "content": f"Contexte documentaire interne :\n\n{rag_context}",
        })
    else:
        messages_payload.append({
            "role": "system",
            "content": (
                "Aucun document interne correspondant trouvé. "
                "Réponds avec tes connaissances générales en droit immobilier français."
            ),
        })

    messages_payload.append({"role": "user", "content": message})

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.2,
                "max_tokens": 800,
                "messages": messages_payload,
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"Erreur API Groq ({r.status_code})"
    except requests.exceptions.Timeout:
        return "⏱️ Délai d'attente dépassé."
    except Exception as e:
        return f"Erreur inattendue : {e}"


# ══════════════════════════════════════════════════════════════════
#  VUES DJANGO
# ══════════════════════════════════════════════════════════════════

@login_required
def chatbot_interface(request):
    """Affiche l'interface du chatbot."""
    return render(request, 'chatbot/interface.html')


@csrf_exempt
@login_required
def chatbot_query(request):
    """
    Point d'entrée unique du chatbot.
    Le routeur IA classe la question en 3 catégories :
      - invoice  → interroge la base de données des factures
      - document → RAG sur les documents techniques internes
      - legal    → Légifrance + Groq
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'response': 'Méthode non autorisée'}, status=405)

    message = ""
    try:
        data = json.loads(request.body or '{}')
        message = (data.get('message') or '').strip()

        if not message:
            return JsonResponse({'success': False, 'response': 'Message vide.'}, status=400)

        # ── Routing IA ────────────────────────────────────────────
        route = _route_message(message)

        if route == "invoice":
            resp = _handle_invoice_query(message, request.user)
            # Fallback legal si aucune facture trouvée
            if resp.startswith("Aucune facture") or "Aucune facture" in resp:
                route = "legal_fallback"
                resp = _handle_legal_query(message)

        elif route == "document":
            resp = _handle_document_query(message)

        else:  # legal
            resp = _handle_legal_query(message)

        # ── Sauvegarde historique ─────────────────────────────────
        ChatbotQuery.objects.create(
            user=request.user,
            message=message,
            response=resp,
            query_type=route,
        )

        return JsonResponse({'success': True, 'response': resp, 'query_type': route})

    except Exception as e:
        error_message = f'Erreur : {e}'
        if request.user.is_authenticated and message:
            ChatbotQuery.objects.create(
                user=request.user,
                message=message,
                response=error_message,
                query_type="unknown",
            )
        return JsonResponse({'success': False, 'response': error_message}, status=500)


@login_required
def chatbot_history(request):
    """Historique des requêtes de l'utilisateur connecté."""
    query_type = (request.GET.get("type") or "").strip()
    search     = (request.GET.get("q") or "").strip()

    qs = ChatbotQuery.objects.filter(user=request.user).order_by("-created_at")

    if query_type:
        qs = qs.filter(query_type=query_type)
    if search:
        qs = qs.filter(message__icontains=search)

    return render(request, "chatbot/history.html", {
        "queries":       qs,
        "selected_type": query_type,
        "search":        search,
    })


# ══════════════════════════════════════════════════════════════════
#  FACTURES (inchangé)
# ══════════════════════════════════════════════════════════════════

INVOICE_STATUS_MAP = {
    'payee': 'Payee', 'payée': 'Payee', 'payé': 'Payee', 'paid': 'Payee',
    'recu': 'Recue', 'reçue': 'Recue',
    'en cours': 'En cours', 'progress': 'En cours',
    'refusee': 'Refusee', 'refusée': 'Refusee', 'rejected': 'Refusee',
    'archivee': 'Archivee', 'archivée': 'Archivee', 'archive': 'Archivee',
    'en retard': 'En retard', 'retard': 'En retard',
}
SUMMARY_KEYWORDS = {'stats', 'résumé', 'resume', 'total', 'synthèse', 'synthese'}
LIST_KEYWORDS    = {'liste', 'toutes', 'all'}


def _user_queryset(user):
    return Facture.objects.select_related('client')


def _invoice_by_id(invoice_id: str, user) -> str:
    try:
        inv = _user_queryset(user).get(id=invoice_id)
        return (
            f"Facture #{inv.id}\n"
            f"• État : {inv.statut}\n"
            f"• Fournisseur : {inv.fournisseur}\n"
            f"• Client : {inv.client.nom if inv.client else '—'}\n"
            f"• Montant : {inv.montant}€\n"
            f"• Pôle : {inv.pole or '—'}\n"
            f"• Dossier : {inv.dossier or '—'}\n"
            f"• Échéance : {inv.echeance.strftime('%d/%m/%Y') if inv.echeance else '—'}\n"
            f"• Titre : {inv.titre or '—'}"
        )
    except Facture.DoesNotExist:
        return f"Aucune facture trouvée avec l'ID {invoice_id}"


def _invoices_by_status(status: str, user) -> str:
    qs = _user_queryset(user).filter(statut=status).order_by('-echeance')[:5]
    if not qs:
        return f"Aucune facture avec le statut {status}."
    lines = [f"Factures '{status}' :"]
    for inv in qs:
        deadline = inv.echeance.strftime('%d/%m') if inv.echeance else '—'
        lines.append(f"• #{inv.id} — {inv.fournisseur} — {inv.montant}€ — {deadline}")
    return "\n".join(lines)


def _invoices_by_supplier(supplier: str, user) -> str:
    qs = _user_queryset(user).filter(fournisseur__icontains=supplier).order_by('-echeance')[:5]
    if not qs:
        return f"Aucune facture pour « {supplier} »"
    lines = [f"Factures — {supplier} :"]
    for inv in qs:
        lines.append(f"• #{inv.id} — {inv.statut} — {inv.montant}€")
    return "\n".join(lines)


def _invoices_all(user, limit=20) -> str:
    qs = _user_queryset(user).order_by('-echeance')[:limit]
    if not qs:
        return "Aucune facture."
    lines = ["Toutes les factures :"]
    for inv in qs:
        lines.append(f"• #{inv.id} — {inv.statut} — {inv.fournisseur} — {inv.montant}€")
    return "\n".join(lines)


def _invoices_summary(user) -> str:
    qs = _user_queryset(user)
    total = qs.count()
    if total == 0:
        return "Aucune facture."
    total_amount = sum(inv.montant or 0 for inv in qs)
    return (
        "Résumé des factures\n"
        f"• Total : {total}\n"
        f"• Montant cumulé : {total_amount:,.2f}€".replace(',', ' ').replace('.', ',')
    )


def _extract_existing_invoice_id(text: str) -> str | None:
    for token in re.findall(r'\b[A-Z]{3,}-[A-Z0-9]{4,}\b', text.upper()):
        if Facture.objects.filter(id=token).exists():
            return token
    return None


def _map_status_from_text(text: str) -> str | None:
    m = text.lower()
    for k in sorted(INVOICE_STATUS_MAP.keys(), key=len, reverse=True):
        if k in m:
            return INVOICE_STATUS_MAP[k]
    return None


def _handle_invoice_query(message: str, user) -> str:
    maybe_id = _extract_existing_invoice_id(message)
    if maybe_id:
        return _invoice_by_id(maybe_id, user)

    low = message.lower()
    if any(w in low for w in SUMMARY_KEYWORDS):
        return _invoices_summary(user)
    if any(w in low for w in LIST_KEYWORDS):
        return _invoices_all(user, limit=20)

    mapped_status = _map_status_from_text(message)
    if mapped_status:
        return _invoices_by_status(mapped_status, user)

    m = re.search(r'fournisseur\s+(.+)$', message, flags=re.I)
    if m:
        supplier = m.group(1).strip()
        if supplier:
            return _invoices_by_supplier(supplier, user)

    return _invoices_by_supplier(message.strip(), user)


# ══════════════════════════════════════════════════════════════════
#  JURIDIQUE (inchangé sauf signature de la fonction)
# ══════════════════════════════════════════════════════════════════

def _handle_legal_query(message: str) -> str:
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key:
        return "Clé API Groq manquante"

    legifrance_context = ""
    try:
        search_result = legifrance_search_generic(message, page_size=5)
        legifrance_context = format_legifrance_context(search_result, max_items=3)
    except Exception as e:
        legifrance_context = f"(Impossible de récupérer des résultats Légifrance : {e})"

    url = "https://api.groq.com/openai/v1/chat/completions"
    base_system_prompt = (
        "Tu es un assistant juridique spécialisé en droit immobilier en France. "
        "Tu t'adresses à des professionnels d'une agence immobilière.\n\n"
        "Quand la question concerne des mesures très récentes (2023, 2024, 2025 : MaPrimeRénov', fiscalité, "
        "taxe foncière, taxe d'habitation résiduelle, locations de courte durée type Airbnb, encadrement des loyers, "
        "calendrier d'interdiction des logements F et G, etc.) :\n"
        "- sois particulièrement prudent,\n"
        "- ne donne pas de dates ou de seuils chiffrés si tu n'es pas sûr,\n"
        "- recommande explicitement de vérifier sur service-public.fr, impots.gouv.fr, ANAH ou Légifrance "
        "et de demander conseil à un professionnel (avocat, notaire, expert-comptable).\n"
        "Précise clairement quand tu donnes une réponse générale ou approximative."
    )

    messages_list = [{"role": "system", "content": base_system_prompt}]
    if legifrance_context:
        messages_list.append({
            "role": "system",
            "content": f"Contexte Légifrance :\n\n{legifrance_context}",
        })
    messages_list.append({"role": "user", "content": message})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages_list,
        "temperature": 0.2,
        "max_tokens": 700,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            answer = data["choices"][0]["message"]["content"].strip()
            if legifrance_context and legifrance_context.startswith("Résultats Légifrance"):
                answer += (
                    "\n\n---\n📚 **Sources Légifrance (métadonnées)**\n"
                    + legifrance_context.replace("Résultats Légifrance (métadonnées) :", "").strip()
                )
            return answer
        try:
            err = r.json()
        except Exception:
            err = r.text
        return f"Erreur API Groq ({r.status_code}) : {err}"
    except requests.exceptions.Timeout:
        return "⏱️ Délai d'attente dépassé."
    except requests.exceptions.ConnectionError as e:
        return f"Erreur de connexion : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"

def _user_queryset(user):
    return Facture.objects.select_related('client')


def _invoice_by_id(invoice_id: str, user) -> str:
    try:
        inv = _user_queryset(user).get(id=invoice_id)
        return (
            f" Facture #{inv.id}\n"
            f"• État : {inv.statut}\n"
            f"• Fournisseur : {inv.fournisseur}\n"
            f"• Client : {inv.client.nom if inv.client else '—'}\n"
            f"• Montant : {inv.montant}€\n"
            f"• Pôle : {inv.pole or '—'}\n"
            f"• Dossier : {inv.dossier or '—'}\n"
            f"• Échéance : {inv.echeance.strftime('%d/%m/%Y') if inv.echeance else '—'}\n"
            f"• Titre : {inv.titre or '—'}"
        )
    except Facture.DoesNotExist:
        return f"Aucune facture trouvée avec l’ID {invoice_id}"


def _invoices_by_status(status: str, user) -> str:
    qs = _user_queryset(user).filter(statut=status).order_by('-echeance')[:5]
    if not qs:
        return f"Aucune facture avec le statut {status}."

    lines = [f" Factures '{status}' :"]
    for inv in qs:
        deadline = inv.echeance.strftime('%d/%m') if inv.echeance else '—'
        lines.append(f"• #{inv.id} — {inv.fournisseur} — {inv.montant}€ — {deadline}")
    return "\n".join(lines)


def _invoices_by_supplier(supplier: str, user) -> str:
    qs = _user_queryset(user).filter(fournisseur__icontains=supplier).order_by('-echeance')[:5]
    if not qs:
        return f" Aucune facture pour « {supplier} »"

    lines = [f" Factures — {supplier} :"]
    for inv in qs:
        lines.append(f"• #{inv.id} — {inv.statut} — {inv.montant}€")
    return "\n".join(lines)


def _invoices_all(user, limit=20) -> str:
    qs = _user_queryset(user).order_by('-echeance')[:limit]
    if not qs:
        return "Aucune facture."

    lines = ["Toutes les factures :"]
    for inv in qs:
        lines.append(f"• #{inv.id} — {inv.statut} — {inv.fournisseur} — {inv.montant}€")
    return "\n".join(lines)


def _invoices_summary(user) -> str:
    qs = _user_queryset(user)
    total = qs.count()
    if total == 0:
        return "Aucune facture."

    total_amount = sum(inv.montant or 0 for inv in qs)
    return (
        "Résumé des factures\n"
        f"• Total : {total}\n"
        f"• Montant cumulé : {total_amount:,.2f}€".replace(',', ' ').replace('.', ',')
    )



def _extract_existing_invoice_id(text: str) -> str | None:
    """
    Cherche un token type FAC-XXXX dans le message et vérifie qu'il existe en base.
    """
    for token in re.findall(r'\b[A-Z]{3,}-[A-Z0-9]{4,}\b', text.upper()):
        if Facture.objects.filter(id=token).exists():
            return token
    return None


def _map_status_from_text(text: str) -> str | None:
    m = text.lower()
    # on teste les clés les plus longues
    for k in sorted(INVOICE_STATUS_MAP.keys(), key=len, reverse=True):
        if k in m:
            return INVOICE_STATUS_MAP[k]
    return None


def _handle_invoice_query(message: str, user) -> str:
    # 1) ID 
    maybe_id = _extract_existing_invoice_id(message)
    if maybe_id:
        return _invoice_by_id(maybe_id, user)

    low = message.lower()

    # 2) Stats / résumé
    if any(w in low for w in SUMMARY_KEYWORDS):
        return _invoices_summary(user)

    # 3) Liste complète 
    if any(w in low for w in LIST_KEYWORDS):
        return _invoices_all(user, limit=20)

    # 4) Filtre par statut 
    mapped_status = _map_status_from_text(message)
    if mapped_status:
        return _invoices_by_status(mapped_status, user)

    # 5) Fournisseur
    m = re.search(r'fournisseur\s+(.+)$', message, flags=re.I)
    if m:
        supplier = m.group(1).strip()
        if supplier:
            return _invoices_by_supplier(supplier, user)

    return _invoices_by_supplier(message.strip(), user)


# Questions juridiques

def _handle_legal_query(message: str) -> str:
    """
    Utilise Légifrance comme base de connaissance (via /search),
    puis Groq (Llama) pour générer la réponse en s'appuyant sur ces résultats
    Spécialisé pour l'immobilier
    """
    
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key:
        return "Clé API Groq manquante"

    # 1) On récupérer des résultats depuis Légifrance
    legifrance_context = ""
    try:
        # LODA_DATE dans legifrance_search_generic
        search_result = legifrance_search_generic(message, page_size=5)
        legifrance_context = format_legifrance_context(search_result, max_items=3)
    except Exception as e:
        # Si Légifrance est KO, on prévient juste le modèle pour ne planter le tout
        legifrance_context = f"(Impossible de récupérer des résultats sur Légifrance pour cette question : {e})"

    # 2) On contextualise la réponse via Groq
    url = "https://api.groq.com/openai/v1/chat/completions"

    base_system_prompt = (
        "Tu es un assistant juridique spécialisé en droit immobilier en France. "
        "Tu t'adresses à des professionnels d'une agence immobilière.\n\n"
        "Quand la question concerne des mesures très récentes (2023, 2024, 2025 : MaPrimeRénov', fiscalité, "
        "taxe foncière, taxe d'habitation résiduelle, locations de courte durée type Airbnb, encadrement des loyers, "
        "calendrier d'interdiction des logements F et G, etc.) :\n"
        "- sois particulièrement prudent,\n"
        "- ne donne pas de dates ou de seuils chiffrés si tu n'es pas sûr,\n"
        "- recommande explicitement de vérifier sur service-public.fr, impots.gouv.fr, ANAH ou Légifrance "
        "et de demander conseil à un professionnel (avocat, notaire, expert-comptable).\n"
        "Précise clairement quand tu donnes une réponse générale ou approximative."
    )



    messages = [
        {"role": "system", "content": base_system_prompt},
    ]

    if legifrance_context:
        messages.append({
            "role": "system",
            "content": (
                "Contexte brut provenant directement de l'API Légifrance. "
                "Utilise-le pour étayer ta réponse :\n\n"
                f"{legifrance_context}"
            )
        })

    messages.append({"role": "user", "content": message})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 700,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            answer = data["choices"][0]["message"]["content"].strip()

            # On ajoute les sources Légifrance à la fin
            if legifrance_context and legifrance_context.startswith("Résultats Légifrance"):
                answer += (
                    "\n\n---\n"
                    "📚 **Sources Légifrance (métadonnées)**\n"
                    + legifrance_context.replace("Résultats Légifrance (métadonnées) :", "").strip()
                )

            return answer
        try:
            err = r.json()
        except Exception:
            err = r.text
        return f" Erreur API Groq ({r.status_code}) : {err}"
    except requests.exceptions.Timeout:
        return "⏱️ Délai d’attente dépassé."
    except requests.exceptions.ConnectionError as e:
        return f" Erreur de connexion : {e}"
    except Exception as e:
        return f" Erreur inattendue : {e}"
