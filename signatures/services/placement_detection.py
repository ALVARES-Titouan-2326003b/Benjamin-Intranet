import os
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .pdf_signing import get_signature_block_metrics


ANCHORS = (
    ("signature", 100),
    ("cachet", 96),
    ("lu et approuve", 94),
    ("bon pour accord", 92),
    ("pour la societe", 84),
    ("le representant", 78),
    ("nom et qualite", 74),
)
MAX_OCR_PAGES = 5


def _normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip().lower()


def _matching_anchor(text):
    normalized = _normalize(text)
    matches = [(label, score) for label, score in ANCHORS if label in normalized]
    return max(matches, key=lambda item: item[1]) if matches else None


def _bounded_position(anchor_x, anchor_y, page_width, page_height, metrics):
    margin = 12.0
    block_width = metrics["block_width"]
    block_height = metrics["block_height"]
    x = min(max(anchor_x, margin), max(page_width - block_width - margin, 0))

    # On privilégie l'espace sous la mention détectée, puis au-dessus si le
    # bloc sortirait de la page.
    y = anchor_y - block_height - margin
    if y < margin:
        y = anchor_y + margin
    y = min(max(y, margin), max(page_height - block_height - margin, 0))
    return (x / page_width) * 100, (y / page_height) * 100


def _native_text_anchors(page, page_number, metrics):
    fragments = []

    def visitor(text, cm, tm, font_dict, font_size):
        cleaned = " ".join((text or "").split())
        if cleaned:
            fragments.append(
                {
                    "text": cleaned,
                    "x": float(tm[4]),
                    "y": float(tm[5]),
                    "font_size": float(font_size or 10),
                }
            )

    extracted = page.extract_text(visitor_text=visitor) or ""
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    suggestions = []
    for fragment in fragments:
        match = _matching_anchor(fragment["text"])
        if not match:
            continue
        anchor, base_score = match
        x_pct, y_pct = _bounded_position(
            fragment["x"],
            fragment["y"],
            page_width,
            page_height,
            metrics,
        )
        suggestions.append(
            {
                "page_number": page_number,
                "x_pct": round(x_pct, 4),
                "y_pct": round(y_pct, 4),
                "confidence": min(base_score, 99),
                "detected_text": fragment["text"][:160],
                "anchor": anchor,
                "source": "text",
            }
        )
    return extracted, suggestions


def _configure_tesseract():
    import pytesseract

    configured = os.getenv("TESSERACT_CMD", "").strip()
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    candidates = [
        configured,
        str(Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
        if local_app_data
        else "",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            break
    pytesseract.get_tesseract_version()
    return pytesseract


def ocr_is_available():
    try:
        _configure_tesseract()
        return True
    except Exception:
        return False


def _ocr_page_anchors(pdf_path, page_index, page_width, page_height, metrics):
    import pypdfium2
    from pytesseract import Output

    pytesseract = _configure_tesseract()
    pdf = pypdfium2.PdfDocument(pdf_path)
    try:
        bitmap = pdf[page_index].render(scale=200 / 72)
        image = bitmap.to_pil().convert("RGB")
        languages = set(pytesseract.get_languages(config=""))
        language = "fra+eng" if {"fra", "eng"}.issubset(languages) else "fra" if "fra" in languages else "eng"
        data = pytesseract.image_to_data(
            image,
            lang=language,
            config="--psm 6",
            output_type=Output.DICT,
            timeout=25,
        )
    finally:
        pdf.close()

    lines = {}
    for index, text in enumerate(data.get("text", [])):
        text = (text or "").strip()
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1
        if not text or confidence < 25:
            continue
        key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )
        item = lines.setdefault(key, {"words": [], "left": None, "bottom": 0, "confidence": []})
        left = int(data["left"][index])
        top = int(data["top"][index])
        height = int(data["height"][index])
        item["words"].append(text)
        item["left"] = left if item["left"] is None else min(item["left"], left)
        item["bottom"] = max(item["bottom"], top + height)
        item["confidence"].append(confidence)

    image_width, image_height = image.size
    suggestions = []
    for line in lines.values():
        text = " ".join(line["words"])
        match = _matching_anchor(text)
        if not match:
            continue
        anchor, base_score = match
        anchor_x = (line["left"] / image_width) * page_width
        anchor_y = (1 - (line["bottom"] / image_height)) * page_height
        x_pct, y_pct = _bounded_position(
            anchor_x,
            anchor_y,
            page_width,
            page_height,
            metrics,
        )
        ocr_confidence = sum(line["confidence"]) / len(line["confidence"])
        suggestions.append(
            {
                "page_number": page_index + 1,
                "x_pct": round(x_pct, 4),
                "y_pct": round(y_pct, 4),
                "confidence": round(min(base_score, ocr_confidence), 1),
                "detected_text": text[:160],
                "anchor": anchor,
                "source": "ocr",
            }
        )
    return suggestions


def _deduplicate(suggestions):
    ordered = sorted(
        suggestions,
        key=lambda item: (item["confidence"], item["page_number"]),
        reverse=True,
    )
    result = []
    for suggestion in ordered:
        duplicate = any(
            existing["page_number"] == suggestion["page_number"]
            and abs(existing["x_pct"] - suggestion["x_pct"]) < 5
            and abs(existing["y_pct"] - suggestion["y_pct"]) < 5
            for existing in result
        )
        if not duplicate:
            result.append(suggestion)
    return result[:8]


def detect_signature_placements(
    document,
    signature_mode="stamp_signature",
    size_scale_pct=100.0,
    signature_mention="",
):
    metrics = get_signature_block_metrics(
        size_scale_pct,
        signature_mode=signature_mode,
        signature_mention=signature_mention,
    )
    reader = PdfReader(document.fichier.path)
    suggestions = []
    pages_without_text = []

    for index, page in enumerate(reader.pages):
        extracted, native_suggestions = _native_text_anchors(page, index + 1, metrics)
        suggestions.extend(native_suggestions)
        if len(_normalize(extracted)) < 20:
            pages_without_text.append(index)

    ocr_available = ocr_is_available()
    ocr_errors = []
    if ocr_available:
        for page_index in pages_without_text[-MAX_OCR_PAGES:]:
            page = reader.pages[page_index]
            try:
                suggestions.extend(
                    _ocr_page_anchors(
                        document.fichier.path,
                        page_index,
                        float(page.mediabox.width),
                        float(page.mediabox.height),
                        metrics,
                    )
                )
            except Exception as exc:
                ocr_errors.append(f"Page {page_index + 1} : {exc}")

    return {
        "suggestions": _deduplicate(suggestions),
        "ocr_available": ocr_available,
        "ocr_pages_analyzed": min(len(pages_without_text), MAX_OCR_PAGES) if ocr_available else 0,
        "pages_without_text": len(pages_without_text),
        "ocr_errors": ocr_errors,
    }
