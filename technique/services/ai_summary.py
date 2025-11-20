import json
import time
import requests
from django.conf import settings

GROQ_API_KEY = getattr(settings, "GROQ_API_KEY", None)
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# Le modèle de llama accepte ~128K tokens.
# Donc on vise ~3000 tokens par chunk ≈ 12000 caractères.
TARGET_TOKENS_PER_CHUNK = 3000
CHARS_PER_TOKEN = 4  
CHUNK_SIZE_CHARS = TARGET_TOKENS_PER_CHUNK * CHARS_PER_TOKEN  # ~12000 chars

# Limites d’affichage 
MAX_RESUME_CHARS = 3000
MAX_FIELD_CHARS = 1000  # prix / dates / conditions / pénalités / délais

# Rate limit / pauses sinon on est bloqués par l’API
SLEEP_BETWEEN_CHUNKS = 5.0  # secondes entre 2 requêtes
MAX_RETRIES_PER_CHUNK = 2   # 1 essai + 1 retry max
RETRY_SLEEP_SECONDS = 5.0   # pause avant de retenter un chunk


SYSTEM_CHUNK = (
    "Tu es un assistant juridique spécialisé en documents immobiliers français "
    "(contrats de réservation VEFA, promesses de vente, permis de construire, PV, etc.). "
    "On te donne UNIQUEMENT UN EXTRAIT du document complet. "
    "Tu DOIS répondre STRICTEMENT en JSON, SANS AUCUN TEXTE AUTOUR, avec EXACTEMENT ces clés :\n"
    "{\n"
    '  "resume": "5 à 7 puces synthétiques sur CE PASSAGE SEULEMENT, sous forme de texte avec des lignes commençant par \'-\'",\n'
    '  "prix": "Infos prix / montants / dépôt de garantie / échéancier trouvées dans CE PASSAGE, sinon chaîne vide",\n'
    '  "dates": "Dates importantes / délais trouvés dans CE PASSAGE, sinon chaîne vide",\n'
    '  "conditions_suspensives": "Conditions suspensives trouvées dans CE PASSAGE, sinon chaîne vide",\n'
    '  "penalites": "Pénalités / conséquences financières trouvées dans CE PASSAGE, sinon chaîne vide",\n'
    '  "delais": "Délais (achèvement, livraison, paiement, notification...) trouvés dans CE PASSAGE, sinon chaîne vide"\n'
    "}\n\n"
    "RÈGLES IMPORTANTES :\n"
    "- Ne recopie PAS des paragraphes entiers, reformule.\n"
    "- Ne parle que de CE PASSAGE, pas du document entier.\n"
    "- Si tu ne vois rien pour un champ (prix/dates/etc.), mets une chaîne vide \"\" pour ce champ.\n"
    "- N'ajoute AUCUNE AUTRE CLÉ.\n"
)


# OUTILS TEXTE / CHUNKS

def _normalize_text(val: str) -> str:
    #On enlève les espaces, etc inutiles
    if val is None:
        return ""
    import re

    txt = str(val)
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")

    lines = []
    for line in txt.split("\n"):
        if not line.strip():
            continue
        line = re.sub(r"[ \t]+", " ", line)
        lines.append(line.strip())

    txt = "\n".join(lines)
    txt = re.sub(r"\n{2,}", "\n", txt)
    return txt.strip()


def _estimate_tokens(text: str) -> int:
    """Estimation des tokens"""
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def _split_into_chunks(text: str) -> list[str]:
    """
    On découpe un texte long en fonction de CHUNK_SIZE_CHARS.
    la longueur des caractères correspond à un nombres de tokens
    """
    text = text or ""
    if not text:
        return []

    size = CHUNK_SIZE_CHARS
    return [text[i:i + size] for i in range(0, len(text), size)]


def _parse_json_or_fallback(content: str) -> dict:
    # Parser en json

    stripped = content.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1:
        candidate = stripped[start:end + 1]
    else:
        candidate = stripped

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        # Fallback
        bullets = []
        for line in stripped.splitlines():
            l = line.strip()
            if l.startswith("-"):
                bullets.append(l)
        if bullets:
            resume = "\n".join(bullets)
        else:
            resume = stripped[:800]  # limite

        data = {
            "resume": resume,
            "prix": "",
            "dates": "",
            "conditions_suspensives": "",
            "penalites": "",
            "delais": "",
        }

    # toutes les clés
    for key in [
        "resume",
        "prix",
        "dates",
        "conditions_suspensives",
        "penalites",
        "delais",
    ]:
        data.setdefault(key, "")

    # nettoyage
    for k in list(data.keys()):
        data[k] = _normalize_text(data[k])

    return data


def _call_groq_chunk(chunk_text: str) -> dict:
    #On fait le chunk
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": SYSTEM_CHUNK},
            {"role": "user", "content": chunk_text},
        ],
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    last_error = None

    for attempt in range(1, MAX_RETRIES_PER_CHUNK + 1):
        try:
            r = requests.post(GROQ_CHAT_URL, json=payload, headers=headers, timeout=60)
            status = r.status_code

            if status == 429:
                last_error = requests.exceptions.HTTPError("429 Too Many Requests")
                print(f"[AI] 429 Too Many Requests sur chunk (tentative {attempt}/{MAX_RETRIES_PER_CHUNK})")
                if attempt < MAX_RETRIES_PER_CHUNK:
                    print(f"[AI] Pause {RETRY_SLEEP_SECONDS}s avant retry...")
                    time.sleep(RETRY_SLEEP_SECONDS)
                    continue
                else:
                    raise last_error

            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            data = _parse_json_or_fallback(content)
            return data

        except Exception as e:
            last_error = e
            print(f"[AI] Erreur sur appel chunk (tentative {attempt}/{MAX_RETRIES_PER_CHUNK}): {e}")
            if attempt < MAX_RETRIES_PER_CHUNK:
                time.sleep(RETRY_SLEEP_SECONDS)
                continue
            else:
                raise

    raise last_error or RuntimeError("Erreur inconnue sur appel Groq")


# RESUME COMPLET DOCUMENT 

def summarize_document(texte: str) -> dict:
    # Résume un document COMPLET

    texte = texte or ""
    if not texte.strip():
        return {
            "resume": "",
            "prix": "Non identifié",
            "dates": "Non identifié",
            "conditions_suspensives": "Non identifié",
            "penalites": "Non identifié",
            "delais": "Non identifié",
        }


    total_chars = len(texte)
    est_tokens = _estimate_tokens(texte)
    print(f"[AI] Taille document : {total_chars} caractères (~{est_tokens} tokens estimés)")

    chunks = _split_into_chunks(texte)
    print(f"[AI] Document découpé en {len(chunks)} chunk(s) de ~{CHUNK_SIZE_CHARS} caractères.")

    all_resume_parts: list[str] = []
    prix_parts: list[str] = []
    dates_parts: list[str] = []
    conditions_parts: list[str] = []
    penalites_parts: list[str] = []
    delais_parts: list[str] = []

    for idx, chunk in enumerate(chunks, start=1):
        print(f"[AI] Traitement du chunk {idx}/{len(chunks)}...")
        try:
            res = _call_groq_chunk(chunk)
        except Exception as e:
            import traceback
            print(f"[AI] Erreur DEFINITIVE sur le chunk {idx}: {e}")
            traceback.print_exc()
            # On continue avec les autres chunks pour ne pas tout perdre
        else:
            if res.get("resume"):
                all_resume_parts.append(res["resume"])
            if res.get("prix"):
                prix_parts.append(res["prix"])
            if res.get("dates"):
                dates_parts.append(res["dates"])
            if res.get("conditions_suspensives"):
                conditions_parts.append(res["conditions_suspensives"])
            if res.get("penalites"):
                penalites_parts.append(res["penalites"])
            if res.get("delais"):
                delais_parts.append(res["delais"])

        # 1 requête → on attend 5s → chunk suivant
        print(f"[AI] Pause {SLEEP_BETWEEN_CHUNKS}s avant le prochain chunk...")
        time.sleep(SLEEP_BETWEEN_CHUNKS)

    # On rassemble les résumés
    resume_global = "\n".join(all_resume_parts)
    resume_global = _normalize_text(resume_global)[:MAX_RESUME_CHARS]

    def _merge_field(parts: list[str]) -> str:
        if not parts:
            return "Non identifié"
        # on supprime les doublons
        merged = "; ".join(dict.fromkeys(parts))
        merged = _normalize_text(merged)[:MAX_FIELD_CHARS]
        return merged or "Non identifié"

    prix = _merge_field(prix_parts)
    dates = _merge_field(dates_parts)
    conditions = _merge_field(conditions_parts)
    penalites = _merge_field(penalites_parts)
    delais = _merge_field(delais_parts)

    return {
        "resume": resume_global,
        "prix": prix,
        "dates": dates,
        "conditions_suspensives": conditions,
        "penalites": penalites,
        "delais": delais,
    }
