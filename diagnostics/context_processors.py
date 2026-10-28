"""Values available in every template."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest


def environment(_request: HttpRequest) -> dict[str, Any]:
    """is_dev is true on a local copy (ENVIRONMENT=dev)"""
    return {"is_dev": settings.IS_DEV}
