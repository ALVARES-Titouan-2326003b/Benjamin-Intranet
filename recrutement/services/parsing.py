from pathlib import Path
from io import BytesIO

def _read_pdf(file_obj) -> str:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return ""
    try:
        reader = PdfReader(file_obj)
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages).strip()
    except Exception:
        return ""

def _read_docx(file_obj) -> str:
    try:
        import docx
    except Exception:
        return ""
    try:
        d = docx.Document(file_obj)
        return "\n".join(p.text for p in d.paragraphs).strip()
    except Exception:
        return ""

def extract_text(django_file) -> str:
    """
    Retourne du texte brut depuis PDF/DOCX/TXT.
    """
    name = (getattr(django_file, "name", "") or "").lower()
    data = django_file.read()
    django_file.seek(0)  # important: reset pour le stockage

    if name.endswith(".pdf"):
        return _read_pdf(BytesIO(data))
    if name.endswith(".docx"):
        return _read_docx(BytesIO(data))
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    # fallback simple
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""
 