"""Vues techniques nécessaires à l'exploitation de production."""

import mimetypes

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import SuspiciousFileOperation
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.utils._os import safe_join
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def health_live(request):
    return JsonResponse({"status": "ok"})


@require_GET
@never_cache
def health_ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        cache.set("healthcheck", "ok", timeout=10)
        if cache.get("healthcheck") != "ok":
            raise RuntimeError("cache indisponible")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


@login_required
@require_GET
def protected_media(request, path):
    """Sert un média uniquement aux utilisateurs authentifiés."""

    try:
        file_path = safe_join(settings.MEDIA_ROOT, path)
    except SuspiciousFileOperation as exc:
        raise Http404 from exc

    try:
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        return FileResponse(open(file_path, "rb"), content_type=content_type)
    except FileNotFoundError as exc:
        raise Http404 from exc
