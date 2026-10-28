"""
Turns what a game posts into Reports and Attachments

1. POST report/new/ with one form field per metadata item. Keys the game wants "indexed" end in
   "*" (older reporters used a leading "!"). Every field is searchable now, so the marks are
   stripped. The response tells the game the report id.
2. POST report/<id>/attachment/ once per 512 KB chunk of each file. Chunks of a file arrive in
   order.
"""

import re
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .games import DEFAULT_GAME
from .grouping import find_or_create_issue
from .models import Attachment, Report

UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]+")


class AttachmentRejected(Exception):
    """An attachment chunk broke one of the ingest limits. The message is fwded to the client"""


def clean_key(key: str) -> str:
    """Remove the old index marks"""
    return key.strip().lstrip("!").rstrip("*").strip()


def clean_value(value: str) -> str:
    """Trim very long values and remove 0 bytes"""
    return value.replace("\x00", "")[: settings.MAX_METADATA_VALUE_LENGTH]


def clean_metadata(form: Mapping[str, str]) -> dict[str, str]:
    """Transform form fields into metadata entries"""
    metadata: dict[str, str] = {}
    for raw_key, value in form.items():
        key = clean_value(clean_key(raw_key))[:100]
        if key and len(metadata) < settings.MAX_METADATA_KEYS:
            metadata[key] = clean_value(value)
    return metadata


def create_report(metadata: dict[str, str]) -> Report:
    """Save a new report and group it into an issue if it's an error"""
    game = metadata.get("title", "").strip() or DEFAULT_GAME
    report = Report(
        game=game[:32],
        motive=metadata.get("motive", "")[:64],
        branch=metadata.get("branch", "")[:128],
        version=metadata.get("name", "")[:128],
        metadata=metadata,
    )
    report.issue = find_or_create_issue(report.game, report.message, report.stack_trace)
    report.save()
    return report


def safe_filename(name: str) -> str:
    """Transform a filename so it can't escape the upload folder"""
    name = UNSAFE_FILENAME_CHARACTERS.sub("_", Path(name).name).lstrip(".")
    return name[:128] or "attachment"


@transaction.atomic
def append_attachment_chunk(report_id: int, chunk: UploadedFile) -> Attachment:
    """
    Append one uploaded chunk to the named attachment on a report.
    Raises Report.DoesNotExist for a non-existing report, or AttachmentRejected if a limit is hit.
    """
    # Locking the report row lets us handle uploads one at a time (a bit hacky, but it works perfectly)
    report = Report.objects.select_for_update().get(pk=report_id)

    upload_window = timedelta(minutes=settings.ATTACHMENT_UPLOAD_WINDOW_MINUTES)
    if timezone.now() - report.received_at > upload_window:
        raise AttachmentRejected("This report is too old to modify.")

    filename = safe_filename(chunk.name or "")
    attachment = report.attachments.filter(filename=filename).first()
    if attachment is None:
        if report.attachments.count() >= settings.MAX_ATTACHMENTS_PER_REPORT:
            raise AttachmentRejected("This report has too many attachments.")
        attachment = Attachment(report=report, filename=filename)

    bytes_so_far = report.attachments.aggregate(total=Sum("size"))["total"] or 0
    if bytes_so_far + chunk.size > settings.MAX_ATTACHMENT_BYTES_PER_REPORT:
        raise AttachmentRejected("This report's attachments are too large.")

    attachment.path.parent.mkdir(parents=True, exist_ok=True)
    with attachment.path.open("ab") as file:
        for piece in chunk.chunks():
            file.write(piece)

    attachment.size = attachment.path.stat().st_size
    attachment.save()

    # Sometimes the thumbnail can get generated while still uploading, delete it and it will regen later
    attachment.thumbnail_path.unlink(missing_ok=True)
    return attachment
