"""The report list and report detail pages"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from ..models import Report
from ..search import search_reports

REPORTS_PER_PAGE = 50
MAX_FILTER_CHOICES = 100


def recent_values(column: str) -> list[str]:
    """The distinct values of a report column sorted by last seen"""
    return list(
        Report.objects.exclude(**{column: ""})
        .values(column)
        .annotate(last_seen=Max("received_at"))
        .order_by("-last_seen")
        .values_list(column, flat=True)[:MAX_FILTER_CHOICES]
    )


def filter_reports(reports: QuerySet[Report], request: HttpRequest) -> QuerySet[Report]:
    """Apply the filters and search box from the query string"""
    for column in ("game", "motive", "branch"):
        if value := request.GET.get(column):
            reports = reports.filter(**{column: value})
    return search_reports(reports, request.GET.get("q", ""))


@login_required
def report_list(request: HttpRequest) -> HttpResponse:
    """All reports filtered/searched, sorted by last seen"""
    reports = filter_reports(Report.objects.all(), request)
    reports = reports.select_related("issue").prefetch_related("attachments").order_by("-pk")
    page = Paginator(reports, REPORTS_PER_PAGE).get_page(request.GET.get("page"))

    return render(
        request,
        "diagnostics/report_list.html",
        {
            "page": page,
            "games": recent_values("game"),
            "motives": recent_values("motive"),
            "branches": recent_values("branch"),
        },
    )


@login_required
def report_detail(request: HttpRequest, report_id: int) -> HttpResponse:
    """A full report"""
    report = get_object_or_404(Report.objects.select_related("issue").prefetch_related("attachments"), pk=report_id)
    return render(request, "diagnostics/report_detail.html", {"report": report})
