"""Top-level URLs. Everything is served under settings.URL_PREFIX (/2/diagnostics/)"""

from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path(settings.URL_PREFIX, include("diagnostics.urls")),
]
