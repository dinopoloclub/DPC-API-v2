"""Delete old reports and their files to free up space"""

import shutil
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from ...models import Issue, Report


class Command(BaseCommand):
    """Deletes reports older than a number of days"""

    help = "Delete reports older than --days days, including their attachments"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--days", type=int, required=True, help="Keep reports this recent")
        parser.add_argument("--dry-run", action="store_true", help="Only say how many would be deleted")

    def handle(self, *args: Any, **options: Any) -> None:
        cutoff = timezone.now() - timedelta(days=options["days"])
        old_reports = Report.objects.filter(received_at__lt=cutoff)
        count = old_reports.count()

        if options["dry_run"]:
            self.stdout.write(f"Would delete {count} reports received before {cutoff:%Y-%m-%d}.")
            return

        for report in old_reports.iterator():
            shutil.rmtree(report.upload_directory, ignore_errors=True)
        old_reports.delete()
        Issue.objects.filter(reports__isnull=True).delete()
        self.stdout.write(f"Deleted {count} reports received before {cutoff:%Y-%m-%d}.")
