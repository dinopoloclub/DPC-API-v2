"""
Database models

Report is a submission from a game. Metadata fields are kept as-is (JSONB column)>
Issue is a group of reports that have the same error fingerprint (grouping.py)
Attachment is a file that comes with a report, ie a screenshot or simjournal. They live at settings.UPLOAD_ROOT.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models.functions import Cast, Lower
from django.utils import timezone

IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# Dont' know if we will really expect anything but .log - expand this as needed
TEXT_EXTENSIONS = {".txt", ".log", ".json"}

# Metadata shown in its own section of the report page rather than in the metadata table
MESSAGE_KEY = "message"
STACK_TRACE_KEY = "stackTrace"


class Issue(models.Model):
    """A group of reports with the same error, so repeated crashes display as one row"""

    class Status(models.TextChoices):
        """State of an issue. A new report on a resolved issue reopens it"""

        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    game = models.CharField(max_length=32)
    fingerprint = models.CharField(max_length=64)
    title = models.CharField(max_length=300)
    culprit = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=16, choices=Status, default=Status.OPEN)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["game", "fingerprint"], name="unique_issue_per_game"),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.title}"


class Report(models.Model):
    """A diagnostic report sent from a game"""

    game = models.CharField(max_length=32, db_index=True)
    motive = models.CharField(max_length=64, blank=True, db_index=True)
    branch = models.CharField(max_length=128, blank=True, db_index=True)
    version = models.CharField(max_length=128, blank=True, db_index=True)
    metadata = models.JSONField(default=dict)
    issue = models.ForeignKey(Issue, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    received_at = models.DateTimeField(default=timezone.now, db_index=True)

    # A lowercase copy of the metadata text. It uses a trg index so full-text is fast.
    search_text = models.GeneratedField(
        expression=Lower(Cast("metadata", output_field=models.TextField())),
        output_field=models.TextField(),
        db_persist=True,
    )

    class Meta:
        indexes = [
            GinIndex(fields=["search_text"], opclasses=["gin_trgm_ops"], name="report_search_trgm"),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.game} {self.motive}"

    @property
    def message(self) -> str:
        """The error message ie "NullReferenceException: Object reference not set..." """
        return str(self.metadata.get(MESSAGE_KEY, ""))

    @property
    def stack_trace(self) -> str:
        """The stack trace of the error if posted"""
        return str(self.metadata.get(STACK_TRACE_KEY, ""))

    @property
    def headline(self) -> str:
        """The first line of the mssage, or the motive"""
        first_line = self.message.strip().split("\n", 1)[0]
        return first_line or self.motive or "Report"

    @property
    def device(self) -> str:
        """The device model of the session"""
        return str(self.metadata.get("deviceModel", ""))

    def other_metadata(self) -> list[tuple[str, str]]:
        """All metadata except the message and stack trace"""
        hidden = {MESSAGE_KEY, STACK_TRACE_KEY}
        return sorted(
            ((key, str(value)) for key, value in self.metadata.items() if key not in hidden),
            key=lambda item: item[0].lower(),
        )

    def screenshot(self) -> "Attachment | None":
        """The first image attachment"""
        return next((a for a in self.attachments.all() if a.is_image), None)

    @property
    def upload_directory(self) -> Path:
        """Attachment disk location"""
        return settings.UPLOAD_ROOT / "reports" / str(self.pk)


class Attachment(models.Model):
    """A file uploaded for a report"""

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=128)
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["filename"]
        constraints = [
            models.UniqueConstraint(fields=["report", "filename"], name="unique_attachment_name"),
        ]

    def __str__(self) -> str:
        return self.filename

    @property
    def path(self) -> Path:
        """Where the file is stored on disk"""
        return self.report.upload_directory / self.filename

    @property
    def thumbnail_path(self) -> Path:
        """Where the thumbnail is cached"""
        return self.report.upload_directory / ".thumbnails" / f"{self.pk}.jpg"

    @property
    def extension(self) -> str:
        """Lowercase extension of the filename"""
        return Path(self.filename).suffix.lower()

    @property
    def is_image(self) -> bool:
        """Is the file an image the browser understands"""
        return self.extension in IMAGE_CONTENT_TYPES

    @property
    def is_text(self) -> bool:
        """Is the file safe to show as text in browser"""
        return self.extension in TEXT_EXTENSIONS

    @property
    def content_type(self) -> str:
        """The content type to serve the file with. Unknown files are always downloaded."""
        if self.is_image:
            return IMAGE_CONTENT_TYPES[self.extension]
        if self.is_text:
            return "text/plain; charset=utf-8"
        return "application/octet-stream"
