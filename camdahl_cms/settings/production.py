import os

from .base import *

DEBUG = os.environ.get("DEBUG", "False") == "True"

# SECURITY WARNING: keep the secret key used in production secret!
# Required — fail loudly at startup rather than silently running with a
# missing/insecure key.
SECRET_KEY = os.environ["SECRET_KEY"]

# SECURITY WARNING: define the correct hosts in production!
# Comma-separated, e.g. "camerondahl.com,www.camerondahl.com"
ALLOWED_HOSTS = os.environ["ALLOWED_HOSTS"].split(",")

if csrf_trusted_origins := os.environ.get("CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS = csrf_trusted_origins.split(",")

# Required — production must use a real database, not the SQLite fallback
# in base.py (SQLite doesn't survive redeploys on most hosting platforms).
if "DATABASE_URL" not in os.environ:
    raise RuntimeError("DATABASE_URL environment variable is required in production.")

# Sends real email via SMTP by default. Falls back to logging emails to the
# console if EMAIL_HOST is unset, so a deploy without email configured yet
# doesn't crash — password reset / notification emails just won't be sent.
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False") == "True"

# Magic links only — password auth is fully disabled in production, not just
# hidden from the login page. Dropping ModelBackend means authenticate() can
# no longer succeed with a username/password, even via a direct POST that
# bypasses the login form.
MAGIC_LINK_LOGIN_ONLY = True
AUTHENTICATION_BACKENDS = [
    "sesame.backends.ModelBackend",
]

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

try:
    from .local import *
except ImportError:
    pass
