"""
Serves attachments to authed users

Only images and plain text are shown in the browser - others are downloaded
"""

from pathlib import Path
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, request
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404
from django.utils.cache import get_conditional_response
from django.utils.http import http_date
from django.views.decorators.http import require_GET

from ..models import Attachment
from ..thumbnails import get_thumbnail

CACHE_FOREVER = "private, max-age=31536000, immutable"
CHECK_EACH_TIME = "private, no-cache"


def cached_file_response(
    request: HttpRequest, attachment: Attachment, path: Path, **kwargs: Any
) -> HttpResponseBase:
    """
    Serve a file so the browser can cache it
    """
    last_modified = int(path.stat().st_mtime)
    response = get_conditional_response(request, last_modified=last_modified)
    if response is None:
        response = FileResponse(path.open("rb"), **kwargs)
        response["Last-Modified"] = http_date(last_modified)

    is_current_version = request.GET.get("v") == str(attachment.size)
    response["Cache-Control"] = CACHE_FOREVER if is_current_version else CHECK_EACH_TIME
    return response

@login_required
@require_GET
def attachment_file(request: HttpRequest, attachment_id: int) -> HttpResponseBase:
    """The attachment. Add ?download=1 to always download it"""
    attachment = get_object_or_404(Attachment.objects.select_related("report"), pk=attachment_id)
    if not attachment.path.exists():
        raise Http404("The file for this attachment is missing.")

    viewable = attachment.is_image or attachment.is_text
    return cached_file_response(
        request,
        attachment,
        attachment.path,
        content_type=attachment.content_type,
        as_attachment=not viewable or "download" in request.GET,
        filename=attachment.filename,
    )


@login_required
@require_GET
def attachment_thumbnail(request: HttpRequest, attachment_id: int) -> HttpResponseBase:
    """A thumbnail of an image attachment"""
    attachment = get_object_or_404(Attachment.objects.select_related("report"), pk=attachment_id)
    thumbnail = get_thumbnail(attachment) if attachment.is_image else None
    if thumbnail is None:
        raise Http404("No preview available.")

    return cached_file_response(request, attachment, thumbnail, content_type="image/jpeg")
