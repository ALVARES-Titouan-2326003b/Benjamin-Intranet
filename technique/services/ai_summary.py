import json
import time
import requests
from django.conf import settings

GROQ_API_KEY = getattr(settings, "GROQ_API_KEY", None)
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

TARGET_TOKENS_PER_CHUNK = 3000
CHARS_PER_TOKEN = 4
CHUNK_SIZE_CHARS = TARGET_TOKENS_PER_CHUNK * CHARS_PER_TOKEN

MAX_RESUME_CHARS = 3000
MAX_FIELD_CHARS = 1000

SLEEP_BETWEEN_CHUNKS = 5.0
MAX_RETRIES_PER_CHUNK = 2
RETRY_SLEEP_SECONDS = 5.0


SYSTEM_CHUNK = (
    "Tu es un assistant juridique spécialisé en documents immobiliers français "
    "(contrats de réservation VEFA, promesses de vente, permis de construire, PV, etc.). "
    "On te donne UNIQUEMENT UN EXTRAIT du document complet.\n\n"

    "Tu DOIS répondre STRICTEMENT en JSON, SANS AUCUN TEXTE AUTOUR, "
    "avec EXACTEMENT ces clés :\n"
    "{\n"
    '  "resume": "ENTRE 5 ET 7 puces MAXIMUM sur CE PASSAGE SEULEMENT, sous forme de texte, chaque ligne commence par \'-\'",\n'
    '  "prix": "Infos prix / montants trouvées dans CE PASSAGE, sinon chaîne vide",\n'
    '  "dates": "Dates importantes trouvées dans CE PASSAGE, sinon chaîne vide",\n'
    '  "conditions_suspensives": "Conditions suspensives trouvées, sinon chaîne vide",\n'
    '  "penalites": "Pénalités trouvées, sinon chaîne vide",\n'
    '  "delais": "Délais trouvés, sinon chaîne vide",\n'
    '  "clauses_importantes": [\n'
    '    "EXTRAITS EXACTS des clauses importantes copiés MOT POUR MOT depuis la clé resume que tu viens de créer"\n'
    '  ]\n'
    "}\n\n"

    "RÈGLES ABSOLUES (À RESPECTER AVANT TOUT) :\n"
    "- Ne parle QUE de ce passage.\n"
    "- Ne reformule JAMAIS une clause importante.\n"
    "- Si un extrait n’est pas présent MOT POUR MOT dans le texte fourni, NE LE METS PAS.\n"
    "- Le tableau clauses_importantes doit contenir au MAXIMUM 5 éléments.\n"
    "- Si plus de 5 clauses sont possibles, garde uniquement les plus importantes.\n"
    "- Le tableau clauses_importantes ne doit contenir aucun doublon.\n"
    "- Les clauses importantes doivent être courtes (1 à 2 phrases maximum).\n"
    "- Chaque clause importante doit être une chaîne de caractères correspondant à la clé resume que tu viens de créer AU CARACTÈRE PRÈS.\n"
    "- Si aucune clause importante n’est clairement identifiable, retourne [].\n"
    "- Si un champ est absent, mets une chaîne vide.\n"
    "- N'ajoute AUCUNE AUTRE CLÉ.\n"
    "- N'invente RIEN.\n"
)


# OUTILS TEXTE / CHUNKS

def _normalize_text(val: str) -> str:
    if val is None:
        return ""
    import re
    txt = str(val).replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in txt.split("\n"):
        if line.strip():
            lines.append(re.sub(r"[ \t]+", " ", line).strip())
    return "\n".join(lines).strip()


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN)) if text else 0


def _split_into_chunks(text: str) -> list[str]:
    if not text:
        return []
    return [text[i:i + CHUNK_SIZE_CHARS] for i in range(0, len(text), CHUNK_SIZE_CHARS)]


def _parse_json_or_fallback(content: str) -> dict:
    stripped = content.strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    candidate = stripped[start:end + 1] if start != -1 and end != -1 else stripped

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        data = {
            "resume": stripped[:800],
            "prix": "",
            "dates": "",
            "conditions_suspensives": "",
            "penalites": "",
            "delais": "",
            "clauses_importantes": [],
        }

    for key in [
        "resume",
        "prix",
        "dates",
        "conditions_suspensives",
        "penalites",
        "delais",
    ]:
        data.setdefault(key, "")

    data.setdefault("clauses_importantes", [])
    if not isinstance(data["clauses_importantes"], list):
        data["clauses_importantes"] = []

    for k in data:
        if isinstance(data[k], str):
            data[k] = _normalize_text(data[k])

    return data


def _call_groq_chunk(chunk_text: str) -> dict:
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 900,
        "messages": [
            {"role": "system", "content": SYSTEM_CHUNK},
            {"role": "user", "content": chunk_text},
        ],
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    for attempt in range(MAX_RETRIES_PER_CHUNK):
        try:
            r = requests.post(GROQ_CHAT_URL, json=payload, headers=headers, timeout=60)
            if r.status_code == 429:
                last_error = requests.exceptions.HTTPError("429 Too Many Requests")
                print(f"[AI] 429 Too Many Requests sur chunk (tentative {attempt+1}/{MAX_RETRIES_PER_CHUNK})")
                if attempt == MAX_RETRIES_PER_CHUNK:
                    raise last_error
                print(f"[AI] Pause {RETRY_SLEEP_SECONDS}s avant retry...")
                time.sleep(RETRY_SLEEP_SECONDS)
                continue

            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            return _parse_json_or_fallback(content)
        except Exception:
            print(f"[AI] Erreur sur appel chunk (tentative {attempt+1}/{MAX_RETRIES_PER_CHUNK}): {e}")
            if attempt == MAX_RETRIES_PER_CHUNK:
                raise
            time.sleep(RETRY_SLEEP_SECONDS)
    return _parse_json_or_fallback("{}")


# RESUME COMPLET DOCUMENT

def summarize_document(texte: str) -> dict:
    if not texte or not texte.strip():
        return {
            "resume": "",
            "prix": "Non identifié",
            "dates": "Non identifié",
            "conditions_suspensives": "Non identifié",
            "penalites": "Non identifié",
            "delais": "Non identifié",
            "clauses_importantes": [],
        }

    print(f"[AI] Taille document : {len(texte)} caractères (~{_estimate_tokens(texte)} tokens estimés)")
    chunks = _split_into_chunks(texte)
    print(f"[AI] Document découpé en {len(chunks)} chunk(s) de ~{CHUNK_SIZE_CHARS} caractères.")
    lastChunk = chunks[-1]

    resume_parts = []
    prix_parts, dates_parts = [], []
    conditions_parts, penalites_parts, delais_parts = [], [], []
    clauses_all = []

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
            if res["resume"]:
                resume_parts.append(res["resume"])
            if res["prix"]:
                prix_parts.append(res["prix"])
            if res["dates"]:
                dates_parts.append(res["dates"])
            if res["conditions_suspensives"]:
                conditions_parts.append(res["conditions_suspensives"])
            if res["penalites"]:
                penalites_parts.append(res["penalites"])
            if res["delais"]:
                delais_parts.append(res["delais"])
            clauses_all.extend(res.get("clauses_importantes", []))

        if chunk == lastChunk:
            continue
        # 1 requête → on attend 5s → chunk suivant
        print(f"[AI] Pause {SLEEP_BETWEEN_CHUNKS}s avant le prochain chunk...")
        time.sleep(SLEEP_BETWEEN_CHUNKS)

    resume = _normalize_text("\n".join(resume_parts))[:MAX_RESUME_CHARS]
    clauses_all = list(set(clauses_all))
    for i in range(len(clauses_all)-1, -1, -1):
        if resume.find(clauses_all[i]) == -1:
            clauses_all.pop(i)

    def _merge(parts):
        if not parts:
            return "Non identifié"
        return _normalize_text("; ".join(dict.fromkeys(parts)))[:MAX_FIELD_CHARS]

    return {
        "resume": resume,
        "prix": _merge(prix_parts),
        "dates": _merge(dates_parts),
        "conditions_suspensives": _merge(conditions_parts),
        "penalites": _merge(penalites_parts),
        "delais": _merge(delais_parts),
        "clauses_importantes": clauses_all,
    }
