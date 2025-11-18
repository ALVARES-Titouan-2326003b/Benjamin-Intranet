import time
import unicodedata
import requests
from django.conf import settings



ENV = getattr(settings, "LEGIFRANCE_ENV", "sandbox").lower()

if ENV == "prod":
    LEGIFRANCE_BASE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
    OAUTH_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
else:
    LEGIFRANCE_BASE_URL = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"
    OAUTH_URL = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"

CLIENT_ID = getattr(settings, "LEGIFRANCE_CLIENT_ID", None)
CLIENT_SECRET = getattr(settings, "LEGIFRANCE_CLIENT_SECRET", None)

# cache en mémoire pour éviter de redemander un token à chaque requête
_token_cache = {
    "access_token": None,
    "expires_at": 0,
}


# On récupère le token OAuth2 

def _get_legifrance_token() -> str:
    """
    Récupère un access_token OAuth2
    token dure ~3600s
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("LEGIFRANCE_CLIENT_ID / LEGIFRANCE_CLIENT_SECRET manquants dans settings.")

    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] - 60 > now:
        return _token_cache["access_token"]

    resp = requests.post(
        OAUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "openid",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    access_token = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + expires_in

    return access_token


# On fait un appel à Legifrance

def _auth_headers() -> dict:
    token = _get_legifrance_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _normalize_query(q: str) -> str:
    """
    Uniformise la requête
    """
    q = q.strip()
    q = unicodedata.normalize("NFD", q)
    q = "".join(c for c in q if unicodedata.category(c) != "Mn")
    return q


def legifrance_search_generic(query: str, fond: str = "LODA_DATE", page_size: int = 5) -> dict:
    """
    Appel POST /search
    """
    url = f"{LEGIFRANCE_BASE_URL}/search"

    normalized_query = _normalize_query(query)

    body = {
        "fond": fond,
        "recherche": {
            "champs": [
                {
                    "typeChamp": "ALL",
                    "operateur": "ET",
                    "criteres": [
                        {
                            "typeRecherche": "UN_DES_MOTS",
                            "valeur": normalized_query,
                            "operateur": "ET",
                        }
                    ],
                }
            ],
            "filtres": [],
            "pageNumber": 1,
            "pageSize": page_size,
            "operateur": "ET",
            "sort": "PERTINENCE",
            "typePagination": "DEFAUT",
        },
    }

    resp = requests.post(url, headers=_auth_headers(), json=body, timeout=15)

    if not resp.ok:
        raise RuntimeError(f"Erreur Légifrance /search {resp.status_code}: {resp.text}")

    data = resp.json()
    nb_results = len(data.get("results") or [])
    return data


def format_legifrance_context(search_result: dict, max_items: int = 3) -> str:
    """
    Transforme la réponse brute /search en texte court à injecter dans le prompt du LLM.

    """
    # Où sont les résultats ?
    results = (
        search_result.get("results")
        or search_result.get("resultsList")
        or search_result.get("resultats")
        or search_result.get("items")
        or []
    )

    if not results:
        # Pas de résultats structurés : on renvoie un aperçu
        try:
            import json
            raw = json.dumps(search_result, ensure_ascii=False)
        except Exception:
            raw = str(search_result)
        return "Aperçu brut de la réponse Légifrance (aucun résultat structuré) :\n" + raw[:1500]

    lines = []
    for item in results[:max_items]:
        nature = (
            item.get("nature")
            or item.get("natureTexte")
            or item.get("typeTexte")
            or "—"
        )
        date_pub = (
            item.get("datePublication")
            or item.get("dateVersion")
            or item.get("date")
            or item.get("signatureDate")
            or "—"
        )
        titre = (
            item.get("title")
            or item.get("titre")
            or item.get("titreText")
            or item.get("textTitle")
            or "—"
        )
        nor = item.get("nor") or "—"
        cid = (
            item.get("cid")
            or item.get("idTexte")
            or item.get("id")
            or item.get("textId")
            or "—"
        )

        lines.append(f"- [{nature}] {titre} (NOR: {nor}, id: {cid}, date: {date_pub})")

    ctx = "Résultats Légifrance (métadonnées) :\n" + "\n".join(lines)
    return ctx


