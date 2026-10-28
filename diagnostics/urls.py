"""
Endpoint URLs, all under /2/diagnostics/.

Their paths match the old server, so a game only needs its base URL changed to https://api.dinopoloclub.com/2/.
"""

from django.urls import path

from .views import api, auth, files, issues, reports

urlpatterns = [
    # Public API for games.
    path("report/new/", api.new_report, name="api_new_report"),
    path("report/<int:report_id>/attachment/", api.upload_attachment, name="api_attachment"),
    path("health/", api.health, name="health"),
    # Signing in.
    path("login/", auth.login_page, name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("auth/slack/", auth.slack_start, name="slack_start"),
    path("auth/slack/callback/", auth.slack_callback, name="slack_callback"),
    # The report browser (Slack sign-in required).
    path("", reports.report_list, name="report_list"),
    path("reports/<int:report_id>/", reports.report_detail, name="report_detail"),
    path("issues/", issues.issue_list, name="issue_list"),
    path("issues/<int:issue_id>/", issues.issue_detail, name="issue_detail"),
    path("issues/<int:issue_id>/status/", issues.issue_set_status, name="issue_set_status"),
    path("files/<int:attachment_id>/", files.attachment_file, name="attachment_file"),
    path("files/<int:attachment_id>/thumbnail/", files.attachment_thumbnail, name="thumbnail"),
]
