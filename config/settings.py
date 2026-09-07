"""
RentFlow — Django settings.

Works in two modes:
  * Development  (python manage.py runserver / python run_desktop.py from source)
  * Desktop build (PyInstaller-frozen .exe on Windows)

All writable data (SQLite database, uploaded documents, generated invoices)
lives in a "data directory" so the installed application never tries to write
inside Program Files:

    RENTFLOW_DATA_DIR  -> override the data folder
                         (defaults to <exe folder>/RentFlow_Data when packaged,
                          to the project root when running from source)
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _is_frozen():
    return getattr(sys, "frozen", False)


# ---------------------------------------------------------------------------
# Data directory (database + media live here, must be writable)
# ---------------------------------------------------------------------------
if _is_frozen():
    _DEFAULT_DATA_DIR = Path(sys.executable).resolve().parent / "RentFlow_Data"
else:
    _DEFAULT_DATA_DIR = BASE_DIR

DATA_DIR = Path(os.environ.get("RENTFLOW_DATA_DIR", str(_DEFAULT_DATA_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "media" / "documents").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "media" / "invoices").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "media" / "profiles").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "media" / "buildings").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "RENTFLOW_SECRET_KEY",
    "rentflow-insecure-dev-key-change-with-RENTFLOW_SECRET_KEY-env-var",
)
DEBUG = os.environ.get("RENTFLOW_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]  # desktop app, bound to 127.0.0.1

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "apps.accounts",
    "apps.properties",
    "apps.payments",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database (SQLite — zero config, perfect for a desktop app)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "rentflow.db",
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email (Gmail SMTP). Leave host user blank -> emails are "sent" to the on-screen
# outbox / console so the app works with zero configuration.
# To enable real delivery set the env vars (or edit the lines below):
#   RENTFLOW_EMAIL_USER      = your Gmail address
#   RENTFLOW_EMAIL_PASSWORD  = a Gmail *App Password* (16 chars, no spaces)
# ---------------------------------------------------------------------------
EMAIL_HOST = os.environ.get("RENTFLOW_EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("RENTFLOW_EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("RENTFLOW_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("RENTFLOW_EMAIL_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get(
    "RENTFLOW_FROM_EMAIL", "RentFlow <rentflow.noreply@gmail.com>"
)
EMAIL_SUBJECT_PREFIX = "[RentFlow] "
if not EMAIL_HOST_USER:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ---------------------------------------------------------------------------
# RentFlow business settings
# ---------------------------------------------------------------------------
RENTFLOW = {
    "COMPANY_NAME": "RentFlow Property Management",
    "COMPANY_SHORT": "RentFlow",
    "ADDRESS": "House 12, Road 5, Dhanmondi, Dhaka 1205",
    "PHONE": "+880 1700 000000",
    "EMAIL": "accounts@rentflow.app",
    "BANK_NAME": "City Bank Ltd.",
    "BANK_ACCOUNT": "1402 3388 7701",
    "BANK_ROUTING": "225123456",
    "BKASH_NUMBER": "01700-000000",
    "RENT_DUE_DAY": 10,  # rent for a month is due on the 10th of that month
}
