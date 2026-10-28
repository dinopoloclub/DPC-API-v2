"""
The public API the games post reports to. No auth, and ratelimited by nginx
"""

import logging
from typing import Any

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..ingest import AttachmentRejected, append_attachment_chunk, clean_metadata, create_report
from ..models import Report

logger = logging.getLogger(__name__)


def ok(**data: Any) -> JsonResponse:
    """A success response"""
    return JsonResponse({"result": "ok", **data})


def error(message: str, status: int) -> JsonResponse:
    """A failure response"""
    return JsonResponse({"result": "error", "message": message}, status=status)


@csrf_exempt
@require_POST
def new_report(request: HttpRequest) -> JsonResponse:
    """Create a report from posted metadata"""
    report = create_report(clean_metadata(request.POST))
    logger.info("Received report %s (%s, %s)", report.pk, report.game, report.motive)
    return ok(reportId=report.pk)


@csrf_exempt
@require_POST
def upload_attachment(request: HttpRequest, report_id: int) -> JsonResponse:
    """Append one chunk of an attachment"""
    chunks = [chunk for field in request.FILES for chunk in request.FILES.getlist(field)]
    if not chunks:
        return error("No file was sent.", status=400)

    try:
        for chunk in chunks:
            append_attachment_chunk(report_id, chunk)
    except Report.DoesNotExist:
        return error("Report not found.", status=404)
    except AttachmentRejected as rejection:
        logger.warning("Rejected attachment for report %s: %s", report_id, rejection)
        return error(str(rejection), status=413)

    return ok()


@require_GET
def health(_request: HttpRequest) -> JsonResponse:
    """Used by Docker to check the server and database are up"""
    connection.ensure_connection()
    return ok()
