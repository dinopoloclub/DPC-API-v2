"""
Sign in with Slack via OpenID Connect

1. slack_start sends the browser to Slack's authorize page.
2. Slack sends the browser back to slack_callback with a one-time code.
3. We swap the code for an access token, then validate with Slack

The views check the user is in our workspace.
see: https://api.slack.com/authentication/sign-in-with-slack
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse

AUTHORIZE_URL = "https://slack.com/openid/connect/authorize"
TOKEN_URL = "https://slack.com/api/openid.connect.token"
USER_INFO_URL = "https://slack.com/api/openid.connect.userInfo"
TIMEOUT_SECONDS = 10


class SlackError(Exception):
    """wrapper for a Slack API exception"""


@dataclass(frozen=True)
class SlackUser:
    """The parts of a Slack profile we use"""

    user_id: str
    team_id: str
    name: str
    email: str
    picture: str


def redirect_uri() -> str:
    """Must match the Redirect URL in the Slack app settings"""
    return settings.SITE_URL + reverse("slack_callback")


def authorize_url(state: str) -> str:
    """The Slack page that asks user to login"""
    params = {
        "response_type": "code",
        "scope": "openid profile email",
        "client_id": settings.SLACK_CLIENT_ID,
        "redirect_uri": redirect_uri(),
        "state": state,
        "team": settings.SLACK_TEAM_ID,  # Skips the "choose a workspace" step.
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def fetch_user(code: str) -> SlackUser:
    """Swap the one-time code from Slack for the signed-in user profile"""
    token = call_slack(
        TOKEN_URL,
        data={
            "client_id": settings.SLACK_CLIENT_ID,
            "client_secret": settings.SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri(),
        },
    )["access_token"]

    profile = call_slack(USER_INFO_URL, headers={"Authorization": f"Bearer {token}"})
    return SlackUser(
        user_id=profile["https://slack.com/user_id"],
        team_id=profile["https://slack.com/team_id"],
        name=profile.get("name", ""),
        email=profile.get("email", ""),
        picture=profile.get("https://slack.com/user_image_48") or profile.get("picture", ""),
    )


def call_slack(url: str, data: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """POST to a Slack API endpoint and return its response, raising SlackError on failure"""
    try:
        response = requests.post(url, data=data, headers=headers, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError) as error:
        raise SlackError(f"Couldn't reach Slack: {error}") from error

    if not payload.get("ok"):
        raise SlackError(f"Slack: {payload.get('error', 'unknown error')}")
    return payload
