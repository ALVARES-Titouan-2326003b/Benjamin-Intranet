from collections import defaultdict

from django.db.models import Count
from django.utils import timezone

from invoices.models import Facture


OPEN_STATUSES = ["received", "ongoing"]


def get_invoice_anomalies(queryset=None):
    qs = queryset or Facture.objects.all()
    qs = qs.select_related("dossier", "fournisseur")
    now = timezone.now()
    anomalies = []

    def add(facture, kind, severity, message):
        anomalies.append(
            {
                "facture": facture,
                "kind": kind,
                "severity": severity,
                "message": message,
            }
        )

    duplicate_keys = (
        qs.values("societe", "affaire", "montant", "numero_facture")
        .exclude(societe="")
        .exclude(affaire="")
        .exclude(numero_facture="")
        .exclude(montant__isnull=True)
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )
    duplicate_lookup = {
        (row["societe"], row["affaire"], row["montant"], row["numero_facture"])
        for row in duplicate_keys
    }

    for facture in qs.order_by("echeance", "id"):
        if facture.montant is None:
            add(facture, "missing_amount", "error", "Montant absent")
        if not facture.echeance:
            add(facture, "missing_due_date", "warning", "Date d'échéance absente")
        if not facture.fournisseur_id:
            add(facture, "missing_supplier", "error", "Fournisseur absent")
        if facture.statut in OPEN_STATUSES and facture.echeance and facture.echeance < now:
            add(facture, "overdue_open", "warning", "Facture échue non payée")

        duplicate_key = (
            facture.societe,
            facture.affaire,
            facture.montant,
            facture.numero_facture,
        )
        if duplicate_key in duplicate_lookup:
            add(facture, "possible_duplicate", "warning", "Doublon potentiel")

    return anomalies


def summarize_anomalies(anomalies):
    counts = defaultdict(int)
    for anomaly in anomalies:
        counts[anomaly["kind"]] += 1
    return ", ".join(f"{kind}: {count}" for kind, count in sorted(counts.items()))
