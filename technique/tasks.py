from celery import shared_task

from technique.models import TechnicalEmail
from technique.services.attachment_processing import process_attachment


@shared_task
def process_email_attachments(email_id):
    email = TechnicalEmail.objects.prefetch_related("attachments").get(pk=email_id)
    results = [process_attachment(item.pk) for item in email.attachments.all()]
    return {
        "email_id": email.pk,
        "launched": len(results),
        "linked": sum(item["status"] == "linked" for item in results),
        "pending": sum(item["status"] == "pending" for item in results),
        "skipped": sum(item["status"] == "skipped" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "results": results,
    }


def enqueue_email_attachment_processing(email):
    if not email.project_id:
        return {"launched": False, "task_id": "", "attachments": 0}
    try:
        task = process_email_attachments.delay(email.pk)
        return {
            "launched": True,
            "task_id": task.id or "",
            "attachments": email.attachments.count(),
        }
    except Exception as exc:
        return {
            "launched": False,
            "task_id": "",
            "attachments": 0,
            "error": str(exc),
        }
