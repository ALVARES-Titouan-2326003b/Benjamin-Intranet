from __future__ import annotations

from decimal import Decimal

from technique.models import ProjectExpense, TechnicalProject, TechnicalProjectHistory


def _stringify(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def _project_snapshot(project: TechnicalProject) -> dict:
    return {
        "reference": project.reference,
        "name": project.name,
        "type": project.type,
        "total_estimated": _stringify(project.total_estimated),
    }


def _expense_snapshot(expense: ProjectExpense) -> dict:
    return {
        "id": expense.pk,
        "label": expense.label,
        "amount": _stringify(expense.amount),
        "is_paid": expense.is_paid,
        "due_date": _stringify(expense.due_date),
        "payment_date": _stringify(expense.payment_date),
        "facture_id": expense.facture_id,
    }


def _diff_snapshots(old_value: dict | None, new_value: dict | None) -> dict:
    old_value = old_value or {}
    new_value = new_value or {}
    keys = sorted(set(old_value.keys()) | set(new_value.keys()))
    changes = {}

    for key in keys:
        if old_value.get(key) != new_value.get(key):
            changes[key] = {
                "old": old_value.get(key),
                "new": new_value.get(key),
            }
    return changes


def log_project_created(project: TechnicalProject, user) -> TechnicalProjectHistory:
    snapshot = _project_snapshot(project)
    return TechnicalProjectHistory.objects.create(
        project=project,
        user=user,
        action_type="project_created",
        target_type="project",
        target_label=project.reference,
        new_value=snapshot,
        changes=_diff_snapshots(None, snapshot),
        summary=f"Projet {project.reference} créé.",
    )


def log_budget_updated(project: TechnicalProject, user, old_total, new_total) -> TechnicalProjectHistory | None:
    old_value = {"total_estimated": _stringify(old_total)}
    new_value = {"total_estimated": _stringify(new_total)}
    changes = _diff_snapshots(old_value, new_value)
    if not changes:
        return None

    return TechnicalProjectHistory.objects.create(
        project=project,
        user=user,
        action_type="budget_updated",
        target_type="project",
        target_label=project.reference,
        old_value=old_value,
        new_value=new_value,
        changes=changes,
        summary=(
            f"Budget prévisionnel mis à jour pour {project.reference} : "
            f"{_stringify(old_total)} EUR -> {_stringify(new_total)} EUR."
        ),
    )


def log_expense_created(expense: ProjectExpense, user) -> TechnicalProjectHistory:
    snapshot = _expense_snapshot(expense)
    return TechnicalProjectHistory.objects.create(
        project=expense.project,
        user=user,
        action_type="expense_created",
        target_type="expense",
        target_label=expense.label,
        new_value=snapshot,
        changes=_diff_snapshots(None, snapshot),
        summary=f"Dépense '{expense.label}' ajoutée au projet {expense.project.reference}.",
    )


def log_expense_updated(
    expense: ProjectExpense,
    user,
    old_snapshot: dict,
    new_snapshot: dict,
) -> TechnicalProjectHistory | None:
    changes = _diff_snapshots(old_snapshot, new_snapshot)
    if not changes:
        return None

    return TechnicalProjectHistory.objects.create(
        project=expense.project,
        user=user,
        action_type="expense_updated",
        target_type="expense",
        target_label=expense.label,
        old_value=old_snapshot,
        new_value=new_snapshot,
        changes=changes,
        summary=f"Dépense '{expense.label}' modifiée sur le projet {expense.project.reference}.",
    )


def log_expense_deleted(project: TechnicalProject, user, old_snapshot: dict) -> TechnicalProjectHistory:
    label = old_snapshot.get("label") or "Dépense"
    return TechnicalProjectHistory.objects.create(
        project=project,
        user=user,
        action_type="expense_deleted",
        target_type="expense",
        target_label=label,
        old_value=old_snapshot,
        changes=_diff_snapshots(old_snapshot, None),
        summary=f"Dépense '{label}' supprimée du projet {project.reference}.",
    )

