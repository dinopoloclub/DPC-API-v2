"""
Django settings for the diagnostics server. Secrets / config from .env
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent


def env_str(name: str, default: str | None = None) -> str:
    """Read a string setting from the environment"""
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"The {name} environment variable must be set.")
    return value


def env_int(name: str, default: int) -> int:
    """Read a number setting from the environment"""
    return int(os.environ.get(name, str(default)))


# "prod" (the default) for the real server
# "dev" for a local copy. Django's debug pages, and always logged in
ENVIRONMENT = env_str("ENVIRONMENT", "prod")
if ENVIRONMENT not in ("dev", "prod"):
    raise ImproperlyConfigured(f'ENVIRONMENT must be "dev" or "prod", not "{ENVIRONMENT}"')
IS_DEV = ENVIRONMENT == "dev"

DEBUG = IS_DEV
SECRET_KEY = env_str("DJANGO_SECRET_KEY", "dev-key" if IS_DEV else None)

# The public address of the server, without a trailing slash (https://api.dinopoloclub.com)
SITE_URL = env_str("SITE_URL", "http://localhost:8000").rstrip("/")

# Every URL this app serves lives under this prefix which is handled by proxy_pass in nginx
URL_PREFIX = "2/diagnostics/"

ALLOWED_HOSTS = [urlparse(SITE_URL).hostname, "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = [SITE_URL]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.postgres",
    "diagnostics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "diagnostics.middleware.DevAutoSignInMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "diagnostics.context_processors.environment",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env_str("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env_int("POSTGRES_PORT", 5432),
        "NAME": env_str("POSTGRES_DB", "diagnostics"),
        "USER": env_str("POSTGRES_USER", "diagnostics"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "diagnostics" if IS_DEV else None),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"connect_timeout": 5},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = env_str("TIME_ZONE", "Pacific/Auckland")
LANGUAGE_CODE = "en-nz"
STATIC_URL = f"/{URL_PREFIX}static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Attachments are never served directly, the view requires sign in
UPLOAD_ROOT = Path(env_str("UPLOAD_ROOT", str(BASE_DIR / "uploads")))

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_METADATA_VALUE_LENGTH = 64 * 1024
MAX_METADATA_KEYS = 200
MAX_ATTACHMENTS_PER_REPORT = 20
MAX_ATTACHMENT_BYTES_PER_REPORT = env_int("MAX_ATTACHMENT_MB_PER_REPORT", 100) * 1024 * 1024
ATTACHMENT_UPLOAD_WINDOW_MINUTES = 10  # no attachments can happen after this is expired


SLACK_CLIENT_ID = env_str("SLACK_CLIENT_ID", "")
SLACK_CLIENT_SECRET = env_str("SLACK_CLIENT_SECRET", "")
SLACK_TEAM_ID = env_str("SLACK_TEAM_ID", "")

if not IS_DEV and not (SLACK_CLIENT_ID and SLACK_CLIENT_SECRET and SLACK_TEAM_ID):
    raise ImproperlyConfigured("SLACK_CLIENT_ID, SLACK_CLIENT_SECRET and SLACK_TEAM_ID must be set.")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "report_list"

# Storing login state
SESSION_COOKIE_PATH = f"/{URL_PREFIX}"
CSRF_COOKIE_PATH = f"/{URL_PREFIX}"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_SECURE = not IS_DEV
CSRF_COOKIE_SECURE = not IS_DEV

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:", "https:"],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.NONE],
    "frame-ancestors": [CSP.NONE],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
