import os
import math
import json
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

SYSTEM = (
    "Tu es un recruteur. Donne un score (0-100) d'adéquation du CV à la fiche de poste, "
    "et explique brièvement en français les points forts et manques. Réponds en JSON strict "
    'du type {"score": 0-100, "explication": "..."}'
)

def score_cv(job_text: str, cv_text: str) -> dict:
    """
    Renvoie le score d'un cv et une explication par rapport à une fiche de poste

    Args:
        job_text (str): texte de la fiche de poste
        cv_text (str): texte du cv
    """
    # Ia ne génère pas de cv 
    if not cv_text or not cv_text.strip():
        return {
            "score": 0,
            "explication": "Impossible de lire le contenu du fichier (PDF scanné, image ou vide)."
        }

    if not GROQ_API_KEY:
        # fallback très simple si pas de clé (compte des mots communs)
        job_tokens = set(job_text.lower().split())
        cv_tokens = set(cv_text.lower().split())
        inter = len(job_tokens & cv_tokens)
        score = min(100, int((inter / (len(job_tokens) + 1)) * 100))
        return {
            "score": score,
            "explication": "Score heuristique sans LLM (clé GROQ absente)."
        }

    payload = {
        "model": MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"FICHE DE POSTE:\n{job_text}\n\nCV:\n{cv_text}"}
        ]
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        r = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=45)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        # Tente de parser du JSON direct
        try:
            parsed = json.loads(content)
            s = float(parsed.get("score", 0))
            s = max(0, min(100, s))
            exp = parsed.get("explication", "")
            return {"score": s, "explication": exp}
        except Exception:
            # Si le modèle parle autour, on nettoie grossièrement
            import re
            m = re.search(r'"score"\s*:\s*(\d{1,3})', content)
            score = float(m.group(1)) if m else 0
            m = re.search(r'"explication"\s*:\s*"([^"]+)"', content, re.S)
            explication = m.group(1) if m else content[:500]
            return {"score": max(0, min(100, score)), "explication": explication}
    except Exception as e:
        return {"score": None, "explication": f"Erreur LLM: {e}"}
 