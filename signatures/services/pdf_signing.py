from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from reportlab.lib.utils import ImageReader
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from signatures.models import Document, SignatureUser, Tampon


STAMP_WIDTH = 140
STAMP_HEIGHT = 140
SIGNATURE_WIDTH = 160
SIGNATURE_HEIGHT = 70
SIGNATURE_OFFSET_X = 30
SIGNATURE_OFFSET_Y = -10
SIGNATURE_TEXT_AREA_HEIGHT = 42
SIGNATURE_TEXT_FONT_SIZE = 11
SIGNATURE_TEXT_MAX_LENGTH = 160


def _scaled(value, scale_pct):
    return value * (scale_pct / 100.0)


def _fit_signature_text(text, width, area_height, scale_pct):
    """Réduit la police si nécessaire pour conserver tout le texte dans la zone."""
    font_size = _scaled(SIGNATURE_TEXT_FONT_SIZE, scale_pct)
    minimum_font_size = _scaled(5, scale_pct)
    vertical_padding = _scaled(6, scale_pct)

    while font_size >= minimum_font_size:
        lines = simpleSplit(text, "Helvetica-Bold", font_size, width)
        line_height = font_size * 1.2
        if len(lines) * line_height <= area_height - vertical_padding:
            return font_size, line_height, lines
        font_size -= _scaled(0.5, scale_pct)

    lines = simpleSplit(text, "Helvetica-Bold", minimum_font_size, width)
    return minimum_font_size, minimum_font_size * 1.2, lines


def _normalize_pdf_image(path, rotate_degrees=0):
    """
    Prépare une image en appliquant l'orientation EXIF avant insertion PDF.
    ReportLab ne corrige pas toujours cette orientation tout seul.
    """
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        if rotate_degrees:
            image = image.rotate(rotate_degrees, expand=True)
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        return image.convert("RGBA" if has_alpha else "RGB")


def _load_pdf_image(path, rotate_degrees=0):
    image = _normalize_pdf_image(path, rotate_degrees=rotate_degrees)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def get_pdf_document_info(document: Document, page_number: int | None = None) -> dict:
    reader = PdfReader(document.fichier.path)
    page_count = len(reader.pages)
    selected_page_number = page_number or page_count
    if selected_page_number < 1 or selected_page_number > page_count:
        raise ValueError("Numéro de page invalide.")
    selected_page = reader.pages[selected_page_number - 1]
    return {
        "page_count": page_count,
        "page_number": selected_page_number,
        "page_width": float(selected_page.mediabox.width),
        "page_height": float(selected_page.mediabox.height),
        "pages": [
            {
                "number": index + 1,
                "width": float(page.mediabox.width),
                "height": float(page.mediabox.height),
            }
            for index, page in enumerate(reader.pages)
        ],
    }


def get_pdf_last_page_info(document: Document) -> dict:
    """Compatibilité avec les appels historiques centrés sur la dernière page."""
    return get_pdf_document_info(document)


def get_signature_block_metrics(
    size_scale_pct: float = 100.0,
    signature_mode: str = "stamp_signature",
    signature_mention: str = "",
) -> dict:
    sig_width = _scaled(SIGNATURE_WIDTH, size_scale_pct)
    sig_height = _scaled(SIGNATURE_HEIGHT, size_scale_pct)
    text_area_height = (
        _scaled(SIGNATURE_TEXT_AREA_HEIGHT, size_scale_pct)
        if signature_mention.strip()
        else 0
    )

    if signature_mode == "signature":
        return {
            "stamp_width": 0,
            "stamp_height": 0,
            "signature_width": sig_width,
            "signature_height": sig_height,
            "signature_offset_x": 0,
            "signature_offset_y": 0,
            "min_x": 0,
            "min_y": 0,
            "block_width": sig_width,
            "image_block_height": sig_height,
            "text_area_height": text_area_height,
            "block_height": sig_height + text_area_height,
        }

    stamp_width = _scaled(STAMP_WIDTH, size_scale_pct)
    stamp_height = _scaled(STAMP_HEIGHT, size_scale_pct)
    sig_offset_x = _scaled(SIGNATURE_OFFSET_X, size_scale_pct)
    sig_offset_y = _scaled(SIGNATURE_OFFSET_Y, size_scale_pct)

    min_x = min(0, sig_offset_x)
    min_y = min(0, sig_offset_y)
    max_x = max(stamp_width, sig_offset_x + sig_width)
    max_y = max(stamp_height, sig_offset_y + sig_height)

    return {
        "stamp_width": stamp_width,
        "stamp_height": stamp_height,
        "signature_width": sig_width,
        "signature_height": sig_height,
        "signature_offset_x": sig_offset_x,
        "signature_offset_y": sig_offset_y,
        "min_x": min_x,
        "min_y": min_y,
        "block_width": max_x - min_x,
        "image_block_height": max_y - min_y,
        "text_area_height": text_area_height,
        "block_height": max_y - min_y + text_area_height,
    }


def signer_pdf_avec_images_position(
    document: Document,
    user,
    pos_x_pct: float,
    pos_y_pct: float,
    size_scale_pct: float = 100.0,
    signature_mode: str = "stamp_signature",
    tampon: Tampon | None = None,
    page_number: int | None = None,
    signature_mention: str = "",
) -> None:
    """
    Signe le PDF en plaçant le bloc tampon+signature à la position donnée
    (en % de la page, à partir de la GAUCHE et du BAS).

    Args:
        document (Document): Document à signer
        user (User): Utilisateur qui signe le document
        pos_x_pct (float): Position x du bloc complet en pourcentage
        pos_y_pct (float): Position y du bloc complet en pourcentage
        size_scale_pct (float): Échelle du bloc tampon+signature
    """

    if signature_mode not in dict(Document.SIGNATURE_MODES):
        raise ValueError("Mode de signature invalide.")
    signature_mention = " ".join((signature_mention or "").split())
    if len(signature_mention) > SIGNATURE_TEXT_MAX_LENGTH:
        raise ValueError(
            f"La mention ne peut pas dépasser {SIGNATURE_TEXT_MAX_LENGTH} caractères."
        )

    # Signature utilisateur et tampon
    try:
        signature_user = SignatureUser.objects.get(user=user)
    except SignatureUser.DoesNotExist:
        raise ValueError("Aucune image de signature configurée pour cet utilisateur.")

    if signature_mode == "stamp_signature":
        tampon = tampon or Tampon.objects.filter(is_active=True).first()
    else:
        tampon = None
    if signature_mode == "stamp_signature" and not tampon:
        raise ValueError("Aucun tampon configuré dans la base.")

    # Lecture du PDF original
    reader = PdfReader(document.fichier.path)
    writer = PdfWriter()

    num_pages = len(reader.pages)
    selected_page_number = page_number or num_pages
    if selected_page_number < 1 or selected_page_number > num_pages:
        raise ValueError("Numéro de page invalide.")
    selected_page = reader.pages[selected_page_number - 1]
    page_width = float(selected_page.mediabox.width)
    page_height = float(selected_page.mediabox.height)

    # Buffer overlay
    overlay_buffer = BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

    signature_path = signature_user.image.path
    tampon_path = tampon.image.path if tampon else None
    # Les signatures scannées arrivent inversées dans le PDF malgré l'aperçu web.
    signature_image = _load_pdf_image(signature_path, rotate_degrees=180)
    tampon_image = _load_pdf_image(tampon_path) if tampon_path else None

    metrics = get_signature_block_metrics(
        size_scale_pct,
        signature_mode=signature_mode,
        signature_mention=signature_mention,
    )

    # Conversion % → coordonnées PDF (origine en bas à gauche)
    block_x = page_width * (pos_x_pct / 100.0)
    block_y = page_height * (pos_y_pct / 100.0)

    # On borne le bloc complet pour éviter qu'une partie du tampon ou de la
    # signature sorte de la page lorsque l'utilisateur place le cadre au bord.
    block_x = min(max(block_x, 0), max(page_width - metrics["block_width"], 0))
    block_y = min(max(block_y, 0), max(page_height - metrics["block_height"], 0))

    element_x = block_x - metrics["min_x"]
    element_y = block_y - metrics["min_y"]

    # Signature légèrement décalée sur le tampon, ou seule dans son bloc.
    signature_x = element_x + metrics["signature_offset_x"]
    signature_y = element_y + metrics["signature_offset_y"]

    # Dessin du tampon
    if signature_mode == "stamp_signature":
        c.drawImage(
            tampon_image,
            element_x,
            element_y,
            width=metrics["stamp_width"],
            height=metrics["stamp_height"],
            mask="auto",
        )

    # Dessin de la signature par-dessus
    c.drawImage(
        signature_image,
        signature_x,
        signature_y,
        width=metrics["signature_width"],
        height=metrics["signature_height"],
        mask="auto",
    )

    if signature_mention:
        font_size, line_height, lines = _fit_signature_text(
            signature_mention,
            metrics["block_width"],
            metrics["text_area_height"],
            size_scale_pct,
        )
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", font_size)
        first_baseline = (
            block_y
            + metrics["block_height"]
            - font_size
            - _scaled(3, size_scale_pct)
        )
        center_x = block_x + (metrics["block_width"] / 2)
        for index, line in enumerate(lines):
            c.drawCentredString(center_x, first_baseline - (index * line_height), line)

    c.showPage()
    c.save()
    overlay_buffer.seek(0)

    overlay_reader = PdfReader(overlay_buffer)
    overlay_page = overlay_reader.pages[0]

    # Fusion sur la page choisie par l'utilisateur.
    for i in range(num_pages):
        page = reader.pages[i]
        if i == selected_page_number - 1:
            page.merge_page(overlay_page)
        writer.add_page(page)

    # Sauvegarde du nouveau PDF signé
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)

    filename = f"{document.pk}_signe.pdf"
    document.signature_mode = signature_mode
    document.signature_mention = signature_mention
    document.tampon = tampon
    document.fichier_signe.save(
        filename,
        ContentFile(output_buffer.read()),
        save=True,
    )
