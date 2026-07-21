from io import BytesIO

import pypdfium2


def render_pdf_page_preview(document, page_number, scale=1.5):
    pdf = pypdfium2.PdfDocument(document.fichier.path)
    try:
        if page_number < 1 or page_number > len(pdf):
            raise ValueError("Numéro de page invalide.")
        page = pdf[page_number - 1]
        try:
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil().convert("RGB")
                output = BytesIO()
                image.save(output, format="PNG", optimize=True)
                return output.getvalue()
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        pdf.close()
