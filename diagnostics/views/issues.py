"""The issue list and issue detail pages"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Min, Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Issue, Report
from .reports import REPORTS_PER_PAGE, filter_reports, recent_values

ISSUES_PER_PAGE = 50

# The "Sort by" drop-down. query string value -> (label, ordering).
ISSUE_SORTS = {
    "recent": ("Last seen", "-last_seen"),
    "frequent": ("Most reports", "-report_count"),
    "new": ("Newest", "-first_seen"),
}


def issues_with_stats() -> QuerySet[Issue]:
    """Issues with their stats attached"""
    a_day_ago = timezone.now() - timedelta(days=1)
    return Issue.objects.annotate(
        report_count=Count("reports"),
        reports_last_day=Count("reports", filter=Q(reports__received_at__gte=a_day_ago)),
        first_seen=Min("reports__received_at"),
        last_seen=Max("reports__received_at"),
    ).filter(report_count__gt=0)


@login_required
def issue_list(request: HttpRequest) -> HttpResponse:
    """Grouped errors sorted by last seen"""
    status = request.GET.get("status", Issue.Status.OPEN)
    sort = request.GET.get("sort", "recent")
    if sort not in ISSUE_SORTS:
        sort = "recent"

    issues = issues_with_stats()
    if status:
        issues = issues.filter(status=status)
    if game := request.GET.get("game"):
        issues = issues.filter(game=game)
    if query := request.GET.get("q", "").strip():
        issues = issues.filter(Q(title__icontains=query) | Q(culprit__icontains=query))

    issues = issues.order_by(ISSUE_SORTS[sort][1], "-pk")
    page = Paginator(issues, ISSUES_PER_PAGE).get_page(request.GET.get("page"))

    return render(
        request,
        "diagnostics/issue_list.html",
        {
            "page": page,
            "status": status,
            "sort": sort,
            "sorts": {key: label for key, (label, _) in ISSUE_SORTS.items()},
            "statuses": Issue.Status.choices,
            "games": recent_values("game"),
        },
    )


@login_required
def issue_detail(request: HttpRequest, issue_id: int) -> HttpResponse:
    """One issue - stack trace, contained reports, and version etc"""
    issue = get_object_or_404(issues_with_stats(), pk=issue_id)
    reports = filter_reports(issue.reports.all(), request)
    reports = reports.select_related("issue").prefetch_related("attachments").order_by("-pk")

    return render(
        request,
        "diagnostics/issue_detail.html",
        {
            "issue": issue,
            "latest_report": issue.reports.order_by("-pk").first(),
            "branches": count_by(issue.reports.all(), "branch"),
            "versions": count_by(issue.reports.all(), "version"),
            "page": Paginator(reports, REPORTS_PER_PAGE).get_page(request.GET.get("page")),
            "statuses": Issue.Status.choices,
        },
    )


def count_by(reports: QuerySet[Report], column: str, limit: int = 8) -> list[tuple[str, int]]:
    """The most common values of a column among given reports"""
    rows = (
        reports.values(column)
        .annotate(count=Count("pk"))
        .order_by("-count", column)
        .values_list(column, "count")[:limit]
    )
    return [(value or "(none)", count) for value, count in rows]


@login_required
@require_POST
def issue_set_status(request: HttpRequest, issue_id: int) -> HttpResponseRedirect:
    """Mark an issue as with a given status"""
    issue = get_object_or_404(Issue, pk=issue_id)
    if request.POST.get("status") in Issue.Status.values:
        issue.status = request.POST["status"]
        issue.save(update_fields=["status"])
    return redirect("issue_detail", issue_id=issue.pk)
