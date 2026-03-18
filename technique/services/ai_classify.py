import json
import time
import requests
import traceback

from django.conf import settings

GROQ_API_KEY  = getattr(settings, "GROQ_API_KEY", None)
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL         = "llama-3.3-70b-versatile"

# Nombre de projets max envoyés au LLM pour éviter de dépasser la fenêtre de contexte
MAX_PROJECTS_IN_PROMPT = 30

MAX_RETRIES = 3     # tentatives max par appel en cas de 429
RETRY_SLEEP = 10.0  # secondes d'attente de base après un 429 (backoff linéaire)
BULK_SLEEP  = 6.0   # pause entre chaque email lors du classement en masse

SYSTEM_PROMPT = (
    "Tu es un assistant de gestion de projets immobiliers pour l'entreprise Benjamin Immobilier. "
    "Ton rôle est d'analyser un email et de déterminer à quel projet technique il appartient, "
    "en te basant sur la liste des projets fournis.\n\n"
    "Tu DOIS répondre STRICTEMENT en JSON, SANS AUCUN TEXTE AUTOUR, avec EXACTEMENT ces clés :\n"
    "{\n"
    '  "project_id": <entier ou null>,\n'
    '  "confidence": <"high" | "medium" | "low">,\n'
    '  "reason": "<explication courte en français (1-2 phrases max)>"\n'
    "}\n\n"
    "REGLES :\n"
    "- Si tu trouves un projet tres probable, mets son id dans project_id et confidence 'high' ou 'medium'.\n"
    "- Si aucun projet ne correspond clairement, mets project_id: null et confidence: 'low'.\n"
    "- Ne mets JAMAIS un project_id qui n'est pas dans la liste fournie.\n"
    "- N'invente rien, ne reformule pas les donnees de l'email.\n"
    "- Reponds UNIQUEMENT en JSON valide.\n"
)


def classify_email(email, projects: list) -> dict:
    """
    Analyse un TechnicalEmail et retourne le projet le plus probable.

    Args:
        email    : instance TechnicalEmail
        projects : liste de TechnicalProject (QuerySet ou list)

    Returns:
        dict : {
            'project_id' : int | None,
            'confidence' : 'high' | 'medium' | 'low',
            'reason'     : str,
            'success'    : bool,
            'error'      : str | None,
        }
    """
    if not GROQ_API_KEY:
        return _err("Cle GROQ_API_KEY manquante dans les parametres Django.")

    projects_list = list(projects)[:MAX_PROJECTS_IN_PROMPT]
    if not projects_list:
        return _err("Aucun projet disponible pour le classement.")

    projects_block = "\n".join(
        f'- id={p.id} | ref="{p.reference}" | nom="{p.name}" | type="{p.get_type_display()}"'
        for p in projects_list
    )

    body_preview = (email.body or "")[:1500].strip()

    user_message = (
        f"## Email a classer\n"
        f"Objet : {email.subject or '(sans objet)'}\n"
        f"Expediteur : {email.sender or '(inconnu)'}\n"
        f"Destinataires : {email.recipients or ''}\n"
        f"Date de reception : {email.received_at.strftime('%d/%m/%Y %H:%M') if email.received_at else ''}\n"
        f"Corps (extrait) :\n{body_preview}\n\n"
        f"## Projets disponibles\n"
        f"{projects_block}\n\n"
        "Quel est le project_id le plus probable ? Reponds en JSON."
    )

    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(GROQ_CHAT_URL, json=payload, headers=headers, timeout=30)

            if response.status_code == 429:
                wait = RETRY_SLEEP * attempt
                print(
                    f"[ai_classify] 429 Too Many Requests — "
                    f"pause {wait}s (tentative {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)
                last_exc = Exception("429 Too Many Requests")
                continue

            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            result  = _parse_response(content)

            valid_ids = {p.id for p in projects_list}
            if result.get("project_id") and result["project_id"] not in valid_ids:
                result["project_id"] = None
                result["confidence"] = "low"
                result["reason"]     = "ID projet retourne par l'IA hors de la liste — classe ignoré."

            result["success"] = True
            result["error"]   = None
            return result

        except Exception as exc:
            last_exc = exc
            print(f"[ai_classify] Erreur tentative {attempt}/{MAX_RETRIES} : {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP)

    traceback.print_exc()
    return _err(f"Echec apres {MAX_RETRIES} tentatives : {last_exc}")


def classify_and_save(email, projects: list, sleep: float = 0.0) -> dict:
    """
    Classifie l'email et met a jour le modele en base si la confiance est suffisante.

    - confidence 'high'   → status = 'classified'  (sauvegarde automatique)
    - confidence 'medium' → status = 'pending'      (suggere, a valider)
    - confidence 'low'    → aucune modification

    Args:
        email    : instance TechnicalEmail
        projects : liste ou QuerySet de TechnicalProject
        sleep    : pause en secondes APRES l'appel (utile pour le bulk, defaut 0)

    Returns:
        dict : resultat de classify_email enrichi de 'saved' (bool)
    """
    result = classify_email(email, projects)

    # Pause post-appel si demandee (bulk uniquement)
    if sleep > 0:
        time.sleep(sleep)

    if not result["success"]:
        result["saved"] = False
        return result

    project_id = result.get("project_id")
    confidence = result.get("confidence", "low")

    if project_id and confidence in ("high", "medium"):
        email.project_id = project_id
        email.status = "classified" if confidence == "high" else "pending"
        email.save(update_fields=["project", "status"])
        result["saved"] = True
        print(
            f"[ai_classify] Email {email.pk} -> projet {project_id} "
            f"(confiance : {confidence}, statut : {email.status})"
        )
    else:
        result["saved"] = False
        print(f"[ai_classify] Email {email.pk} -> non classe (confiance : {confidence})")

    return result



def _parse_response(content: str) -> dict:
    """Parse la reponse JSON du LLM avec fallback."""
    stripped  = content.strip()
    start     = stripped.find("{")
    end       = stripped.rfind("}")
    candidate = stripped[start : end + 1] if start != -1 and end != -1 else stripped

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return {
            "project_id": None,
            "confidence": "low",
            "reason":     f"Reponse IA non parsable : {content[:200]}",
        }

    return {
        "project_id": data.get("project_id"),
        "confidence": data.get("confidence", "low"),
        "reason":     data.get("reason", ""),
    }


def _err(message: str) -> dict:
    return {
        "project_id": None,
        "confidence": "low",
        "reason":     message,
        "success":    False,
        "error":      message,
        "saved":      False,
    }