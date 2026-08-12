from django.core.management.base import BaseCommand, CommandError

from invoices.models import Facture
from invoices.views import synchronize_configured_invoice_workbook


class Command(BaseCommand):
    help = "Synchronise toutes les factures vers le classeur Excel configuré."

    def add_arguments(self, parser):
        parser.add_argument(
            "--invoice-id",
            action="append",
            dest="invoice_ids",
            help="Limite la synchronisation à cet ID de facture (option répétable).",
        )

    def handle(self, *args, **options):
        queryset = Facture.objects.select_related(
            "societe",
            "dossier",
            "fournisseur",
            "demandeur",
        ).order_by("date_soumission", "id")
        invoice_ids = options.get("invoice_ids") or []
        if invoice_ids:
            queryset = queryset.filter(pk__in=invoice_ids)

        total = queryset.count()
        successes = 0
        failures = 0
        for invoice in queryset.iterator():
            result = synchronize_configured_invoice_workbook(invoice)
            if result is None:
                raise CommandError(
                    "INVOICE_EXCEL_SYNC_PATH est vide : la synchronisation Excel est désactivée."
                )
            if result:
                successes += 1
                self.stdout.write(f"OK {invoice.pk}")
            else:
                failures += 1
                self.stderr.write(f"ERREUR {invoice.pk}")

        message = f"Synchronisation Excel : {successes}/{total} réussie(s), {failures} échec(s)."
        if failures:
            raise CommandError(message)
        self.stdout.write(self.style.SUCCESS(message))
