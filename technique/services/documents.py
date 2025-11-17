# technique/services/documents.py
from recrutement.services.parsing import extract_text as _extract_text_cv


def extract_text_from_file(django_file) -> str:
    """
    Extraire le texte brut des fichiers
    Et on reprend le fichier parseur deja utilisé pour les cvs
    """
    texte = _extract_text_cv(django_file) or ""
    return texte
