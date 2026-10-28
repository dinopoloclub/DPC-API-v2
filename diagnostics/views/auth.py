"""Signing in with Slack, and signing out. See slack.py"""

import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .. import slack

logger = logging.getLogger(__name__)


def safe_next_url(request: HttpRequest, url: str | None) -> str:
    """Where to go after signing in. Only pages on this site are allowed"""
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return resolve_url(settings.LOGIN_REDIRECT_URL)


@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
    """The "Sign in with Slack" page"""
    next_url = safe_next_url(request, request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(next_url)
    return render(request, "diagnostics/login.html", {"next_url": next_url})


@require_GET
def slack_start(request: HttpRequest) -> HttpResponseRedirect:
    """Send the browser to Slack to sign in"""
    state = secrets.token_urlsafe(32)
    request.session["slack_state"] = state
    request.session["next_url"] = safe_next_url(request, request.GET.get("next"))
    return redirect(slack.authorize_url(state))


@require_GET
def slack_callback(request: HttpRequest) -> HttpResponseRedirect:
    """Slack sends the browser back here after the login flow"""
    expected_state = request.session.pop("slack_state", None)
    next_url = request.session.pop("next_url", None)

    if not expected_state or not secrets.compare_digest(request.GET.get("state", ""), expected_state):
        return login_failed(request, "That sign-in link has expired. Please try again.")

    if "error" in request.GET:
        return login_failed(request, "Slack sign-in was cancelled.")

    try:
        slack_user = slack.fetch_user(request.GET.get("code", ""))
    except slack.SlackError as error:
        logger.warning("Slack sign-in failed: %s", error)
        return login_failed(request, "Couldn't sign in with Slack. Please try again.")

    if slack_user.team_id != settings.SLACK_TEAM_ID:
        logger.warning("Rejected sign-in from Slack workspace %s", slack_user.team_id)
        return login_failed(request, "Wrong team ID.")

    user, _ = get_user_model().objects.update_or_create(
        username=slack_user.user_id,
        defaults={"first_name": slack_user.name[:150], "email": slack_user.email},
    )
    login(request, user)
    request.session["avatar_url"] = slack_user.picture
    return redirect(safe_next_url(request, next_url))


def login_failed(request: HttpRequest, message: str) -> HttpResponseRedirect:
    """Go back to the login page and show an error"""
    messages.error(request, message)
    return redirect("login")


@require_POST
def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """Sign out"""
    logout(request)
    return redirect("login")
