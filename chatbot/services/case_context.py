import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from invoices.views import visible_invoices_for
from technique.models import TechnicalProject
from user_access.user_test_functions import can_view_technical_dossiers


STOP_WORDS = {
    "affaire",
    "avec",
    "dans",
    "dossier",
    "etat",
    "faire",
    "quel",
    "quelle",
    "quelles",
    "quels",
    "resume",
    "synthese",
}


@dataclass(frozen=True)
class CaseResolution:
    project: TechnicalProject | None
    alternatives: tuple[TechnicalProject, ...] = ()

    @property
    def is_ambiguous(self):
        return self.project is None and bool(self.alternatives)


@dataclass(frozen=True)
class CaseContext:
    project: TechnicalProject
    prompt: str
    fallback_answer: str
    sources: tuple[tuple[str, str], ...]


def _normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def visible_projects_for(user):
    """Retourne uniquement les dossiers visibles dans les écrans métier."""
    if not getattr(user, "is_authenticated", False):
        return TechnicalProject.objects.none()
    if not can_view_technical_dossiers(user):
        return TechnicalProject.objects.none()
    return TechnicalProject.objects.select_related("societe")


def resolve_case(message, user):
    """Résout une référence ou un nom sans révéler les dossiers non autorisés."""
    normalized_message = _normalize(message)
    words = {
        word
        for word in normalized_message.split()
        if len(word) >= 3 and word not in STOP_WORDS
    }
    scored = []
    for project in visible_projects_for(user).only(
        "id", "reference", "name", "affaire", "societe__nom"
    ):
        reference = _normalize(project.reference)
        name = _normalize(project.name)
        affaire = _normalize(project.affaire)
        score = 0
        if reference and reference in normalized_message:
            score = 100
        elif name and name in normalized_message:
            score = 90
        else:
            haystack = f"{reference} {name} {affaire}"
            score = sum(10 for word in words if word in haystack)
        if score:
            scored.append((score, project))

    if not scored:
        return CaseResolution(project=None)

    best_score = max(score for score, _project in scored)
    best = tuple(project for score, project in scored if score == best_score)
    if len(best) == 1:
        return CaseResolution(project=best[0])
    return CaseResolution(project=None, alternatives=best[:5])


def _money(value):
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")


def _date(value):
    return value.strftime("%d/%m/%Y") if value else "—"


def _source_section(sources):
    if not sources:
        return ""
    rows = ["", "---", "**Sources internes consultables**"]
    rows.extend(f"- [{label}]({url})" for label, url in sources)
    return "\n".join(rows)


def build_case_context(project, user):
    """Construit un instantané borné du dossier avec des sources autorisées."""
    invoices = list(
        visible_invoices_for(
            user,
            project.facture_set.select_related("fournisseur", "societe"),
        ).order_by("-date_soumission", "-id")[:20]
    )
    expenses = list(project.expenses.select_related("facture").order_by("due_date", "id")[:20])
    key_dates = list(
        project.key_dates.select_related("action").prefetch_related("documents").order_by("date", "id")[:15]
    )
    actions = list(
        project.actions.select_related("assigned_to")
        .exclude(status__in=["done", "cancelled"])
        .order_by("due_date", "id")[:15]
    )
    documents = []
    if can_view_technical_dossiers(user):
        documents = list(project.documents.order_by("-created_at")[:8])
    administrative_activities = list(
        project.activite_set.select_related("responsable")
        .exclude(statut__in=["done", "cancelled"])
        .order_by("date", "id")[:15]
    )
    custom_values = list(
        project.custom_field_values.select_related("field")
        .filter(field__is_active=True, field__show_in_detail=True)
        .order_by("field__sort_order", "field__label")[:20]
    )

    invoice_total = sum((Decimal(str(invoice.montant or 0)) for invoice in invoices), Decimal("0"))
    engaged = sum((expense.amount for expense in expenses), Decimal("0"))
    paid = sum((expense.amount for expense in expenses if expense.is_paid), Decimal("0"))
    remaining = project.total_estimated - engaged

    lines = [
        f"DOSSIER : {project.reference} — {project.name}",
        f"Société : {project.societe.nom}",
        f"Statut : {project.get_status_display()}",
        f"Affaire : {project.affaire or '—'}",
        f"Adresse : {project.adresse_bien or '—'}",
        "",
        "SYNTHÈSE FINANCIÈRE",
        f"Budget prévu : {_money(project.total_estimated)}",
        f"Dépenses engagées : {_money(engaged)}",
        f"Dépenses payées : {_money(paid)}",
        f"Reste à engager : {_money(remaining)}",
        f"Factures visibles : {len(invoices)} pour {_money(invoice_total)}",
        "",
        "FACTURES VISIBLES",
    ]
    lines.extend(
        f"- {invoice.id} | n° {invoice.numero_facture or '—'} | {invoice.fournisseur} | "
        f"{_money(invoice.montant)} | {invoice.get_statut_display()} | "
        f"pôle {invoice.get_service_display() or '—'} | facture {_date(invoice.date_facture)} | "
        f"échéance {_date(invoice.echeance)}"
        + (f" | commentaire : {invoice.commentaire_compta}" if invoice.commentaire_compta else "")
        for invoice in invoices
    )
    if not invoices:
        lines.append("- Aucune facture visible pour cet utilisateur.")

    lines.extend(["", "DATES CLÉS"])
    lines.extend(
        f"- {_date(item.date)} | {item.label} | {item.get_status_display() or 'Sans statut'}"
        + (f" | {item.comment}" if item.comment else "")
        for item in key_dates
    )
    if not key_dates:
        lines.append("- Aucune date clé.")

    lines.extend(["", "ACTIONS"])
    for item in actions:
        responsible = (
            item.assigned_to.get_full_name() or item.assigned_to.username
            if item.assigned_to
            else "—"
        )
        overdue = " | EN RETARD" if item.due_date and item.due_date < timezone.localdate() else ""
        lines.append(
            f"- {item.title} | {item.get_status_display()} | priorité {item.get_priority_display()} | "
            f"échéance {_date(item.due_date)} | responsable {responsible}{overdue}"
        )
    if not actions:
        lines.append("- Aucune action ouverte.")

    lines.extend(["", "ACTIVITÉS ADMINISTRATIVES OUVERTES"])
    for item in administrative_activities:
        responsible = (
            item.responsable.get_full_name() or item.responsable.username
            if item.responsable
            else "—"
        )
        lines.append(
            f"- {item.titre or 'Activité'} | {item.get_statut_display()} | "
            f"priorité {item.get_priorite_display()} | date {_date(item.date)} | responsable {responsible}"
            + (f" | {item.commentaire}" if item.commentaire else "")
        )
    if not administrative_activities:
        lines.append("- Aucune activité administrative ouverte.")

    lines.extend(["", "DONNÉES ADMINISTRATIVES DU DOSSIER"])
    lines.extend(
        [
            f"- Type : {project.get_type_dossier_display()}",
            f"- Activité métier : {project.get_activite_metier_display()}",
            f"- État administratif : {project.get_etat_display()}",
            f"- Catégorie : {project.categorie or '—'}",
            f"- Date de promesse : {_date(project.date_promesse)}",
            f"- Date DG : {_date(project.date_dg)}",
            f"- Dépôt permis : {_date(project.depot_permis)}",
            f"- Obtention permis : {_date(project.obtention_permis)}",
            f"- Date de réitération : {_date(project.date_reiteration)}",
        ]
    )
    lines.extend(f"- {item.field.label} : {item.value or '—'}" for item in custom_values)

    lines.extend(["", "DOCUMENTS TECHNIQUES AUTORISÉS"])
    for document in documents:
        excerpt = " ".join((document.resume or document.texte_brut or "").split())[:900]
        lines.append(f"- {document.titre}" + (f" : {excerpt}" if excerpt else ""))
    if not documents:
        lines.append("- Aucun document technique accessible.")

    sources = [
        (f"Dossier technique {project.reference}", reverse("technique:dossier_detail", args=[project.pk])),
        (f"Dossier administratif {project.reference}", reverse("admin_dossier_detail", args=[project.pk])),
    ]
    sources.extend(
        (f"Facture {invoice.id}", reverse("invoices:detail", args=[invoice.pk]))
        for invoice in invoices[:8]
    )
    sources.extend(
        (f"Document : {document.titre}", reverse("technique:documents_detail", args=[document.pk]))
        for document in documents[:5]
    )

    fallback = [
        f"## {project.reference} — {project.name}",
        f"- Société : {project.societe.nom}",
        f"- Statut : {project.get_status_display()}",
        f"- Budget : {_money(project.total_estimated)} ; engagé : {_money(engaged)} ; payé : {_money(paid)}",
        f"- Factures visibles : {len(invoices)}, pour un total de {_money(invoice_total)}",
        f"- Dates clés : {len(key_dates)} ; actions ouvertes : {len(actions)} ; "
        f"activités administratives ouvertes : {len(administrative_activities)} ; "
        f"documents accessibles : {len(documents)}",
    ]
    upcoming_date = next(
        (item for item in key_dates if item.date >= timezone.localdate()),
        None,
    )
    if upcoming_date:
        fallback.append(f"- Prochaine date : {_date(upcoming_date.date)} — {upcoming_date.label}")
    fallback_answer = "\n".join(fallback) + _source_section(sources)
    return CaseContext(project, "\n".join(lines), fallback_answer, tuple(sources))


def append_sources(answer, sources):
    return answer.rstrip() + "\n" + _source_section(sources)
