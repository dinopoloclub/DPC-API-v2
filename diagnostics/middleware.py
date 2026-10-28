"""
Request middleware. Basically just for development, lets us be always signed in on local machine.
Requires ENVIRONMENT=dev in .env
"""

from collections.abc import Callable

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import HttpRequest, HttpResponse

DEV_USERNAME = "dev"


class DevAutoSignInMiddleware:
    """
    When ENVIRONMENT=dev, signs every visitor in as a local "dev" user, so a local copy can be used
    without setting up Slack. Does nothing when ENVIRONMENT=prod
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if settings.IS_DEV and not request.user.is_authenticated:
            user, _ = get_user_model().objects.get_or_create(
                username=DEV_USERNAME, defaults={"first_name": "Local Dev"}
            )
            login(request, user)
        return self.get_response(request)
