"""Validation serveur commune des fichiers téléversés."""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


MIME_BY_EXTENSION = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    ".txt": {"text/plain", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
    ".jpg": {"image/jpeg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "application/octet-stream"},
}

SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".doc": (bytes.fromhex("D0CF11E0A1B11AE1"),),
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


def validate_uploaded_file(upload, allowed_extensions: set[str]) -> None:
    """Contrôle taille, extension, MIME déclaré et signature binaire."""

    max_size = getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)
    if upload.size > max_size:
        raise ValidationError(
            f"Le fichier dépasse la taille maximale autorisée ({max_size // (1024 * 1024)} Mo)."
        )

    extension = Path(upload.name or "").suffix.lower()
    if extension not in allowed_extensions:
        raise ValidationError("Format de fichier non autorisé.")

    content_type = (getattr(upload, "content_type", "") or "").lower()
    accepted_mimes = MIME_BY_EXTENSION.get(extension, set())
    if content_type and accepted_mimes and content_type not in accepted_mimes:
        raise ValidationError("Le type MIME du fichier ne correspond pas à son extension.")

    position = upload.tell() if hasattr(upload, "tell") else 0
    header = upload.read(16)
    upload.seek(position)

    if extension == ".txt":
        if b"\x00" in header:
            raise ValidationError("Le fichier texte contient des données binaires.")
        return

    signatures = SIGNATURES.get(extension, ())
    if signatures and not any(header.startswith(signature) for signature in signatures):
        raise ValidationError("La signature du fichier ne correspond pas au format annoncé.")
