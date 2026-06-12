import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP

from django.core.files.base import ContentFile
from django.utils import timezone

from invoices.models import ExportCegidRun, Facture
from invoices.services.quality import get_invoice_anomalies, summarize_anomalies


FIELD_SEPARATOR = ";"


def ascii_clean(value, max_length=None):
    text = "" if value is None else str(value)
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[\r\n;]+", " ", ascii_text)
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    if max_length:
        return ascii_text[:max_length]
    return ascii_text


def format_amount(value):
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"


def build_cegid_line(facture):
    due_date = facture.echeance.strftime("%Y%m%d") if facture.echeance else ""
    fields = [
        ascii_clean(facture.id, 30),
        ascii_clean(facture.service, 100),
        ascii_clean(facture.dossier, 120),
        ascii_clean(facture.fournisseur, 120),
        ascii_clean(facture.client, 120),
        format_amount(facture.montant),
        ascii_clean(facture.statut, 30),
        due_date,
        ascii_clean(facture.titre, 160),
    ]
    return FIELD_SEPARATOR.join(fields)


def get_export_queryset(period_start=None, period_end=None):
    qs = Facture.objects.select_related("dossier", "fournisseur", "client").order_by("id")
    if period_start:
        qs = qs.filter(echeance__date__gte=period_start)
    if period_end:
        qs = qs.filter(echeance__date__lte=period_end)
    return qs


def generate_cegid_export(user=None, period_start=None, period_end=None):
    run = ExportCegidRun.objects.create(
        triggered_by=user if getattr(user, "is_authenticated", False) else None,
        period_start=period_start,
        period_end=period_end,
    )

    try:
        queryset = get_export_queryset(period_start=period_start, period_end=period_end)
        invoices = list(queryset)
        anomalies = get_invoice_anomalies(queryset)
        lines = [build_cegid_line(facture) for facture in invoices]
        content = "\n".join(lines)
        if content:
            content += "\n"

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pre_export_cegid_{timestamp}.txt"
        run.file.save(filename, ContentFile(content.encode("ascii")), save=False)
        run.status = "success"
        run.line_count = len(lines)
        run.total_amount = sum((facture.montant or 0) for facture in invoices)
        run.anomaly_count = len(anomalies)
        run.warning_summary = summarize_anomalies(anomalies)
        run.completed_at = timezone.now()
        run.save()
    except Exception as exc:
        run.status = "error"
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_message", "completed_at"])

    return run
