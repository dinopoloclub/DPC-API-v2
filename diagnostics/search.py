"""
The report search box

Search syntax:

    nullreference           reports where any field contains "nullreference" (case-insensitive)
    "object reference"      an exact phrase
    -editor                 reports where no field contains "editor"
    branch:main             a specific field contains a value (any metadata key works)
    #1234                   the report with id 1234

All terms must match
"""

import re
import shlex
from dataclasses import dataclass, field

from django.db.models import QuerySet
from django.db.models.fields.json import KeyTextTransform
from django.db.models.lookups import IContains

from .models import Report

# A # followed by any amount of numbers
REPORT_ID = re.compile(r"^#(\d+)$")
# An alphanumeric keyname (or underscore) : value
FIELD_FILTER = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.+)$")
# Field names that refer to report columns
COLUMN_FIELDS = {"game", "motive", "branch", "version"}


@dataclass
class SearchQuery:
    """A parsed search box query"""

    report_ids: list[int] = field(default_factory=list)
    field_filters: list[tuple[str, str]] = field(default_factory=list)
    included_text: list[str] = field(default_factory=list)
    excluded_text: list[str] = field(default_factory=list)


def split_terms(query: str) -> list[str]:
    """Split a query on spaces but keeping "quoted phrases" together"""
    try:
        return shlex.split(query)
    except ValueError:  # An unclosed quote; fall back to plain words.
        return query.split()


def parse_query(query: str) -> SearchQuery:
    """Split each part of the string into arguments"""
    parsed = SearchQuery()
    for term in split_terms(query):
        if match := REPORT_ID.match(term):
            parsed.report_ids.append(int(match.group(1)))
        elif match := FIELD_FILTER.match(term):
            parsed.field_filters.append((match.group(1), match.group(2)))
        elif term.startswith("-") and len(term) > 1:
            parsed.excluded_text.append(term[1:].lower())
        else:
            parsed.included_text.append(term.lower())
    return parsed


def search_reports(reports: QuerySet[Report], query: str) -> QuerySet[Report]:
    """Do the actual report lookup"""
    parsed = parse_query(query)

    if parsed.report_ids:
        reports = reports.filter(pk__in=parsed.report_ids)

    for key, value in parsed.field_filters:
        if key in COLUMN_FIELDS:
            reports = reports.filter(**{f"{key}__icontains": value})
        else:
            reports = reports.filter(IContains(KeyTextTransform(key, "metadata"), value))

    for text in parsed.included_text:
        reports = reports.filter(search_text__contains=text)
    for text in parsed.excluded_text:
        reports = reports.exclude(search_text__contains=text)

    return reports
