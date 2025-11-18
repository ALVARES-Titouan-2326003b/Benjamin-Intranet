from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from signatures.models import Document, SignatureUser, Tampon


def signer_pdf_avec_images_position(document: Document, user, pos_x_pct: float, pos_y_pct: float) -> None:
    """
    Signe le PDF en plaçant le bloc tampon+signature à la position donnée
    (en % de la page, à partir de la GAUCHE et du BAS).
    """

    # Signature utilisateur (CEO) et tampon
    try:
        signature_user = SignatureUser.objects.get(user=user)
    except SignatureUser.DoesNotExist:
        raise ValueError("Aucune image de signature configurée pour cet utilisateur.")

    tampon = Tampon.objects.first()
    if not tampon:
        raise ValueError("Aucun tampon configuré dans la base.")

    # Lecture du PDF original
    reader = PdfReader(document.fichier.path)
    writer = PdfWriter()

    last_page = reader.pages[-1]
    page_width = float(last_page.mediabox.width)
    page_height = float(last_page.mediabox.height)

    # Buffer overlay
    overlay_buffer = BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

    signature_path = signature_user.image.path
    tampon_path = tampon.image.path

    # Tailles en points
    stamp_width, stamp_height = 140, 140
    sig_width, sig_height = 160, 70

    # Conversion % → coordonnées PDF (origine en bas à gauche)
    tampon_x = page_width * (pos_x_pct / 100.0)
    tampon_y = page_height * (pos_y_pct / 100.0)

    # Signature légèrement décalée sur le tampon
    signature_x = tampon_x + 30
    signature_y = tampon_y - 10

    # Dessin du tampon
    c.drawImage(
        tampon_path,
        tampon_x,
        tampon_y,
        width=stamp_width,
        height=stamp_height,
        mask="auto",
    )

    # Dessin de la signature par-dessus
    c.drawImage(
        signature_path,
        signature_x,
        signature_y,
        width=sig_width,
        height=sig_height,
        mask="auto",
    )

    c.showPage()
    c.save()
    overlay_buffer.seek(0)

    overlay_reader = PdfReader(overlay_buffer)
    overlay_page = overlay_reader.pages[0]

    # Fusion sur la dernière page
    num_pages = len(reader.pages)
    for i in range(num_pages):
        page = reader.pages[i]
        if i == num_pages - 1:
            page.merge_page(overlay_page)
        writer.add_page(page)

    # Sauvegarde du nouveau PDF signé
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)

    filename = f"{document.pk}_signe.pdf"
    document.fichier_signe.save(
        filename,
        ContentFile(output_buffer.read()),
        save=True,
    )
