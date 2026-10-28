"""Re-apply the grouping rules in grouping.py to every report"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from ...grouping import find_or_create_issue
from ...models import Issue, Report


class Command(BaseCommand):
    """
    Run this after changing the rules in grouping.py. Reports move to the issue that matches their
    new fingerprint, and issues left with no reports are deleted
    """

    help = "Re-group every report into issues using the current rules in grouping.py"

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        moved = 0
        for report in Report.objects.order_by("pk").iterator():
            issue = find_or_create_issue(report.game, report.message, report.stack_trace, reopen_resolved=False)
            if report.issue_id != (issue.pk if issue else None):
                report.issue = issue
                report.save(update_fields=["issue"])
                moved += 1

        deleted, _ = Issue.objects.filter(reports__isnull=True).delete()
        self.stdout.write(f"Moved {moved} reports. Deleted {deleted} empty issues.")
