"""
Serves attachments to authed users

Only images and plain text are shown in the browser - others are downloaded
"""

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from ..models import Attachment
from ..thumbnails import get_thumbnail


@login_required
@require_GET
def attachment_file(request: HttpRequest, attachment_id: int) -> FileResponse:
    """The attachment. Add ?download=1 to always download it"""
    attachment = get_object_or_404(Attachment.objects.select_related("report"), pk=attachment_id)
    if not attachment.path.exists():
        raise Http404("The file for this attachment is missing.")

    viewable = attachment.is_image or attachment.is_text
    return FileResponse(
        attachment.path.open("rb"),
        content_type=attachment.content_type,
        as_attachment=not viewable or "download" in request.GET,
        filename=attachment.filename,
    )


@login_required
@require_GET
def attachment_thumbnail(_request: HttpRequest, attachment_id: int) -> FileResponse:
    """A thumbnail of an image attachment"""
    attachment = get_object_or_404(Attachment.objects.select_related("report"), pk=attachment_id)
    thumbnail = get_thumbnail(attachment) if attachment.is_image else None
    if thumbnail is None:
        raise Http404("No preview available.")

    response = FileResponse(thumbnail.open("rb"), content_type="image/jpeg")
    response["Cache-Control"] = "private, max-age=86400"
    return response
