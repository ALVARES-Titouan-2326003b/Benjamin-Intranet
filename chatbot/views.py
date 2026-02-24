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

    try:
        data = json.loads(request.body or '{}')
        message = (data.get('message') or '').strip()
        if not message:
            return JsonResponse({'success': False, 'response': 'Message vide.'}, status=400)

        #route = None

        if _is_invoice_query(message):
            #route = "invoice"
            resp = _handle_invoice_query(message, request.user)

            # Fallback si aucune facture trouvée
            if resp.startswith("❌ Aucune facture") or resp.startswith("🕳️ Aucune facture"):
                #route = "legal_fallback"
                resp = _handle_legal_query(message)
        else:
            #route = "legal"
            resp = _handle_legal_query(message)

        return JsonResponse({'success': True, 'response': resp})
    except Exception as e:
        return JsonResponse({'success': False, 'response': f'Erreur: {e}'}, status=500)


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


def _is_invoice_query(msg: str) -> bool:
    m = msg.lower()
    has_id = bool(re.search(r'\b[A-Z]{3,}-[A-Z0-9]{4,}\b', msg))
    keywords = ['facture', 'factures', 'fournisseur', 'statut', 'liste', 'total', 'combien', 'stats']
    return has_id or any(k in m for k in keywords)


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
        return f"❌ Aucune facture trouvée avec l’ID {invoice_id}"


def _invoices_by_status(status: str, user) -> str:
    qs = _user_queryset(user).filter(statut=status).order_by('-echeance')[:5]
    if not qs:
        return f"❌ Aucune facture avec le statut {status}."

    lines = [f" Factures '{status}' :"]
    for inv in qs:
        deadline = inv.echeance.strftime('%d/%m') if inv.echeance else '—'
        lines.append(f"• #{inv.id} — {inv.fournisseur} — {inv.montant}€ — {deadline}")
    return "\n".join(lines)


def _invoices_by_supplier(supplier: str, user) -> str:
    qs = _user_queryset(user).filter(fournisseur__icontains=supplier).order_by('-echeance')[:5]
    if not qs:
        return f"❌ Aucune facture pour « {supplier} »"

    lines = [f" Factures — {supplier} :"]
    for inv in qs:
        lines.append(f"• #{inv.id} — {inv.statut} — {inv.montant}€")
    return "\n".join(lines)


def _invoices_all(user, limit=20) -> str:
    qs = _user_queryset(user).order_by('-echeance')[:limit]
    if not qs:
        return "🕳️ Aucune facture."

    lines = ["📄 Toutes les factures :"]
    for inv in qs:
        lines.append(f"• #{inv.id} — {inv.statut} — {inv.fournisseur} — {inv.montant}€")
    return "\n".join(lines)


def _invoices_summary(user) -> str:
    qs = _user_queryset(user)
    total = qs.count()
    if total == 0:
        return "🕳️ Aucune facture."

    total_amount = sum(inv.montant or 0 for inv in qs)
    return (
        "📊 Résumé des factures\n"
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
