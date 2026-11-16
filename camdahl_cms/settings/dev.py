import os

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True") == "True"

# SECURITY WARNING: keep the secret key used in production secret!
# Falls back to a fixed dev-only key so `manage.py runserver` works out of
# the box without an .env file.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure--k*#8!z0g50w(2ou_y^7yrusangptpu$zf^@^0+$45$#bhp5k2"
)

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# Absolute URLs in API responses point at the local runserver (see base.py).
WAGTAILAPI_BASE_URL = os.environ.get("WAGTAILAPI_BASE_URL", "http://127.0.0.1:8000")

# Prints emails to the console by default. Set EMAIL_BACKEND (and the rest
# of the EMAIL_* vars below) in .env to test against a real SMTP server.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False") == "True"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False") == "True"


try:
    from .local import *
except ImportError:
    pass
