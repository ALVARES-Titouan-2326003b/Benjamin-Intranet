from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image
from reportlab.pdfgen import canvas

from signatures.models import Document
from signatures.services.placement_detection import detect_signature_placements


@pytest.mark.django_db
def test_detecte_un_repere_textuel_sans_ocr():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(595, 842))
    pdf.drawString(80, 180, "Signature du representant")
    pdf.showPage()
    pdf.save()

    document = Document.objects.create(titre="Document avec zone de signature")
    document.fichier.save(
        "document_repere_signature.pdf",
        ContentFile(buffer.getvalue()),
        save=True,
    )

    with patch(
        "signatures.services.placement_detection.ocr_is_available",
        return_value=False,
    ):
        result = detect_signature_placements(
            document,
            signature_mode="signature",
        )

    assert result["ocr_available"] is False
    assert result["suggestions"]
    suggestion = result["suggestions"][0]
    assert suggestion["page_number"] == 1
    assert suggestion["anchor"] == "signature"
    assert suggestion["source"] == "text"
    assert 0 <= suggestion["x_pct"] <= 100
    assert 0 <= suggestion["y_pct"] <= 100


@pytest.mark.django_db
def test_endpoint_retourne_les_suggestions(
    client,
    document_pdf_simple,
    signature_user_ceo,
):
    client.force_login(signature_user_ceo.user)
    detection = {
        "suggestions": [
            {
                "page_number": 1,
                "x_pct": 12.0,
                "y_pct": 18.0,
                "confidence": 95,
                "detected_text": "Signature",
                "anchor": "signature",
                "source": "text",
            }
        ],
        "ocr_available": False,
        "ocr_pages_analyzed": 0,
        "pages_without_text": 0,
        "ocr_errors": [],
    }

    with patch("signatures.views.detect_signature_placements", return_value=detection) as mocked:
        response = client.get(
            reverse("signatures:placement_suggestions", args=[document_pdf_simple.pk]),
            {"signature_mode": "signature", "size_scale_pct": "125"},
        )

    assert response.status_code == 200
    assert response.json()["suggestions"] == detection["suggestions"]
    mocked.assert_called_once_with(
        document_pdf_simple,
        signature_mode="signature",
        size_scale_pct=125.0,
        signature_mention="",
    )


@pytest.mark.django_db
def test_ecran_de_placement_commence_sur_la_derniere_page(
    client,
    document_pdf_multi,
    signature_user_ceo,
):
    client.force_login(signature_user_ceo.user)

    response = client.get(
        reverse("signatures:placer_signature", args=[document_pdf_multi.pk])
    )

    assert response.status_code == 200
    assert response.context["pdf_page_count"] == 3
    assert response.context["pdf_page_number"] == 3
    assert b'name="page_number"' in response.content
    assert b'id="analyze-placement"' in response.content
    assert b'<img id="pdf-preview"' in response.content
    assert b'id="signature-mention-choice"' in response.content
    assert "Bon pour remboursement" in response.content.decode()
    assert b"widthPoints: 160.0" in response.content
    assert b"widthPoints: 160,0" not in response.content
    assert response.content.count(b"let dragging = false;") == 1


@pytest.mark.django_db
def test_apercu_pdf_est_rendu_en_png(
    client,
    document_pdf_multi,
    signature_user_ceo,
):
    client.force_login(signature_user_ceo.user)

    response = client.get(
        reverse("signatures:page_preview", args=[document_pdf_multi.pk]),
        {"page": 2},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(BytesIO(response.content))
    assert image.width > 500
    assert image.height > image.width
