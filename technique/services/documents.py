from io import BytesIO


def _read_pdf(file_obj) -> str:
    """Retourne le texte contenu dans un fichier PDF."""
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return ""
    try:
        reader = PdfReader(file_obj)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception:
        return ""


def _read_docx(file_obj) -> str:
    """Retourne le texte contenu dans un fichier DOCX."""
    try:
        import docx
    except Exception:
        return ""
    try:
        document = docx.Document(file_obj)
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
    except Exception:
        return ""


def _extract_text(django_file) -> str:
    """Retourne le texte brut d'un fichier PDF, DOCX ou texte."""
    name = (getattr(django_file, "name", "") or "").lower()
    data = django_file.read()
    django_file.seek(0)

    if name.endswith(".pdf"):
        return _read_pdf(BytesIO(data))
    if name.endswith(".docx"):
        return _read_docx(BytesIO(data))
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_text_from_file(django_file) -> str:
    """
    Extraire le texte brut des fichiers
    Le flux est repositionné après lecture afin de permettre son stockage.
    """
    texte = _extract_text(django_file) or ""
    return texte
